"""LangChain agent that analyzes RAG results and returns structured answers."""

from __future__ import annotations

import logging
import time
import json
import re
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.tools.query_tool import query_messages_tool
from app.tools.split_range_tool import split_range

from app.agents.llm_manager import get_llm_manager

from app.utils.agent_log import log_agent_result, DetailedTimingCallback

logger = logging.getLogger("app.agents.langchain_agent")

try:
    from langchain.agents import create_agent
    from langchain_openai import ChatOpenAI
    from langgraph.checkpoint.memory import InMemorySaver
except Exception as exc:
    raise ImportError(
        "langchain and provider packages are required for LangChainAgent."
    ) from exc


class LangChainAgent:
    """LangChain agent that analyzes RAG results and returns structured answers.

    Parameters
    - model: model name passed to LangChain's OpenAI when no `llm_instance` is provided.
    - llm_instance: optional pre-initialized LLM object (preferred).
    - use_memory: attach MemorySaver when True.
    - agent_kwargs: forwarded to `create_agent`.
    """

    def __init__(
        self,
        model: str = "gpt-4.1-mini",
        llm_instance: Optional[Any] = None,
        use_memory: bool = False,
        agent_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.model = model
        self.use_memory = use_memory
        self.agent_kwargs = agent_kwargs or {}

        if llm_instance is not None:
            self.llm_instance = llm_instance
        else:
            manager = get_llm_manager()
            self.llm_instance = manager.get_llm_for_agent(model=self.model)

    async def run(
        self,
        question: str,
        group_uniid: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        top_k: int = 50,
        analysis: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        use_agent: bool = True,
    ) -> Dict[str, Any]:
        """Run the LangChain agent and return analyzed results.

        Returns:
            Dict containing:
            - answer: Synthesized answer based on search results
            - metadata: Contains chunk_ids
        """

        if analysis is None:
            from app.services.query_service import QueryService

            now = (
                __import__("datetime")
                .datetime.now()
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S")
            )

            svc = QueryService()

            analysis = svc.analyze_query(question, history=None, now_str=now)

        query_messages = query_messages_tool(
            group_uniid=group_uniid,
            start_time=start_time,
            end_time=end_time,
            top_k=top_k,
            analysis=analysis,
        )

        tools: List[Any] = [query_messages, split_range]

        checkpointer = InMemorySaver() if self.use_memory else None

        create_kwargs = dict(self.agent_kwargs)
        if checkpointer is not None:
            create_kwargs["checkpointer"] = checkpointer

        logger.debug(
            "Creating agent: model=%s use_memory=%s tools=%s",
            self.model,
            self.use_memory,
            [getattr(t, "name", getattr(t, "__name__", str(t))) for t in tools],
        )

        effective_model = model or self.model

        if self.llm_instance is not None and model is None:
            llm_obj = self.llm_instance
        else:
            if not settings.openai_api_key:
                raise RuntimeError(
                    "OpenAI API key not configured in settings.openai_api_key"
                )
            try:
                manager = get_llm_manager()
                llm_obj = manager.get_llm_for_agent(model=effective_model)
            except Exception:
                llm_obj = ChatOpenAI(
                    model=effective_model, openai_api_key=settings.openai_api_key
                )

        try:
            agent = create_agent(model=llm_obj, tools=tools, **create_kwargs)
        except Exception as e:
            logger.exception("Failed to create agent: %s", e)
            raise

        try:
            timing_callback = DetailedTimingCallback()

            # 根據模型類型選擇最佳 Prompt
            # Gemini 使用簡化版，OpenAI 可用完整版
            if "gemini" in effective_model.lower():
                sys_msg = """You are an intelligent assistant analyzing LINE group messages.

                    WORKFLOW:
                    1. Use query_messages tool to search for relevant information
                    2. Examine the returned results and their scores (0-100)
                    3. Make decision based on results:
                    - If you have results with score > 30: synthesize answer from those chunks
                    - If all scores < 30 or no results: respond that information is not available

                    IMPORTANT:
                    - Always use the tool BEFORE forming your answer
                    - Answer must be in 繁體中文

                    Output after using tool:
                    {
                        "answer": "your answer or '無法找到問題相關的答案，請再輸入更詳細的資訊'",
                    }

                    RULES:
                    When you CAN answer (have relevant results with score > 30):
                    - Combine information from the most relevant chunks
                    - Organize the information logically
                    - Example: {{"answer": "居服人員的照顧..."}}
                    """
            else:
                sys_msg = """You are an intelligent assistant analyzing LINE group messages.

                    WORKFLOW:
                    1. Use query_messages tool to search for relevant information
                    2. Examine the returned results and their scores (0-100)
                    3. Make decision based on results:
                    - If you have results with score > 30: synthesize answer from those chunks
                    - If all scores < 30 or no results: respond that information is not available

                    IMPORTANT:
                    - Always use the tool BEFORE forming your answer
                    - Answer must be in 繁體中文

                    Output after using tool:
                    {
                        "answer": "your answer or '無法找到問題相關的答案，請再輸入更詳細的資訊'",
                        "chunk_ids": "comma-separated chunk_ids OR empty string"
                    }

                    RULES:
                    When you CAN answer (have relevant results with score > 30):
                    - Combine information from the most relevant chunks
                    - Organize the information logically
                    - Include only the chunk_ids you actually referenced
                    - Example: {{"answer": "居服人員的照顧...", "chunk_ids": "msg_001,msg_002"}}
                    """

            payload = {
                "messages": [
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": question},
                ],
            }
            configurable = {
                "configurable": {"thread_id": group_uniid},
                "callbacks": [timing_callback],
                # "recursion_limit": 8, # refer to scripts\multi_query.py
            }

            logger.debug(
                "Calling agent.ainvoke: question=%s model=%s", question, effective_model
            )

            result = await agent.ainvoke(payload, configurable)

            log_agent_result(result, enabled=True)

            timing_callback.log_summary()

        except Exception as exc:
            logger.exception(
                "Agent invocation failed. question=%s group_uniid=%s model=%s error=%s",
                question,
                group_uniid,
                effective_model,
                exc,
            )
            raise

        try:
            parsed_result = self._parse_agent_output(result, model=effective_model)
            return parsed_result
        except Exception as e:
            logger.exception("Failed to parse agent output: %s", e)

    def _parse_agent_output(
        self, agent_output: Dict[str, Any], model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Parse agent output to extract answer, chunk_ids, and metadata.

        Args:
            agent_output: The raw output from agent.ainvoke

        Returns:
            Structured dict with answer, confidence, and metadata
        """
        messages = agent_output.get("messages", [])

        # Find the agent's final response (last AI message)
        agent_response = None
        for msg in reversed(messages):
            if hasattr(msg, "type"):
                msg_type = msg.type
                if msg_type in ("ai", "assistant"):
                    content = msg.content if hasattr(msg, "content") else ""
                    if isinstance(content, str) and content.strip():
                        agent_response = content.strip()
                        break
            elif isinstance(msg, dict):
                msg_type = msg.get("type") or msg.get("role")
                if msg_type in ("ai", "assistant"):
                    content = msg.get("content", "")
                    if isinstance(content, str) and content.strip():
                        agent_response = content.strip()
                        break

        if not agent_response:
            raise ValueError("No agent response found in messages")

        # Parse the JSON response from agent
        cleaned_response = agent_response.strip()
        if cleaned_response.startswith("```"):
            cleaned_response = re.sub(r"^```(?:json)?\s*", "", cleaned_response)
            cleaned_response = re.sub(r"\s*```$", "", cleaned_response)
            cleaned_response = cleaned_response.strip()

        try:
            parsed_json = json.loads(cleaned_response)
            answer = parsed_json.get("answer", "")
            chunk_ids_str = parsed_json.get("chunk_ids", "")
        except json.JSONDecodeError as e:
            if model and "gemini" in model.lower():
                pass
            else:
                logger.warning(f"Failed to parse agent JSON response: {e}")

            answer = agent_response
            chunk_ids_str = ""

        metadata: Dict[str, Any] = {
            "chunk_ids": chunk_ids_str,
        }

        result_dict: Dict[str, Any] = {
            "answer": answer,
            "metadata": metadata,
        }

        logger.info(
            "Parsed agent output: answer_length=%d, chunk_ids=%s",
            len(answer),
            chunk_ids_str,
        )

        return result_dict


__all__ = ["LangChainAgent"]
