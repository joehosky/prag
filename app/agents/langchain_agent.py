"""LangChain agent that analyzes RAG results and returns structured answers."""

from __future__ import annotations

import logging
from datetime import datetime
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
    from langchain.agents import create_agent, AgentState
    from langchain.agents.middleware import before_model
    from langchain_openai import ChatOpenAI
    from langgraph.checkpoint.memory import InMemorySaver
    from langchain_core.messages import RemoveMessage
    from langgraph.graph.message import REMOVE_ALL_MESSAGES
    from langgraph.runtime import Runtime
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
    - max_messages: maximum number of messages to keep (default: 5, 0=unlimited)
    - agent_kwargs: forwarded to `create_agent`.
    """

    def __init__(
        self,
        model: str = "gpt-4.1-mini",
        llm_instance: Optional[Any] = None,
        use_memory: bool = False,
        max_messages: int = 5,
        agent_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.model = model
        self.use_memory = use_memory
        self.max_messages = max_messages
        self.agent_kwargs = agent_kwargs or {}
        self.checkpointer = InMemorySaver() if use_memory else None

        if llm_instance is not None:
            self.llm_instance = llm_instance
        else:
            manager = get_llm_manager()
            self.llm_instance = manager.get_llm_for_agent(model=self.model)

        logger.info(
            "langchain: llm_model=%s, llm_keep_memory=%s, max_messages=%s",
            self.model,
            self.use_memory,
            self.max_messages if self.use_memory else "N/A",
        )

    def _create_trim_middleware(self):
        max_msgs = self.max_messages

        @before_model
        def trim_messages_middleware(
            state: AgentState, runtime: Runtime
        ) -> dict[str, Any] | None:
            messages = state["messages"]

            if len(messages) <= max_msgs:
                return None

            # 從後往前保留 max_msgs 則，但要確保 tool_calls 和 tool response 成對
            # 策略：找到第一個「完整對話輪次」的起點（human 或 system message）
            keep_count = max_msgs
            start_idx = len(messages) - keep_count

            # 往前調整 start_idx 直到找到 human/system message（避免從 tool 開始）
            while start_idx > 0 and start_idx < len(messages):
                msg = messages[start_idx]
                msg_type = getattr(msg, "type", None)
                # 如果是 tool message，往前移一位（保留對應的 ai message）
                if msg_type == "tool":
                    start_idx -= 1
                else:
                    break

            messages_to_remove = messages[:start_idx]

            if messages_to_remove:
                logger.debug(
                    "Memory trim: total=%d, removing=%d oldest messages (from idx 0 to %d), keeping=%d latest",
                    len(messages),
                    len(messages_to_remove),
                    start_idx - 1,
                    len(messages) - start_idx,
                )

                return {
                    "messages": [RemoveMessage(id=m.id) for m in messages_to_remove]
                }

            return None

        return trim_messages_middleware

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

        create_kwargs = dict(self.agent_kwargs)
        if self.checkpointer is not None:
            create_kwargs["checkpointer"] = self.checkpointer

        if self.use_memory and self.max_messages > 0:
            trim_middleware = self._create_trim_middleware()
            create_kwargs["middleware"] = [trim_middleware]

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

        current_year = datetime.now().year
        current_date = datetime.now().strftime("%Y-%m-%d")
        time_hint = f"\nIMPORTANT: Current date is {current_date}. When user mentions '八月份' without year, assume current year {current_year}."

        if "gemini" in effective_model.lower():
            sys_msg = """You are an intelligent assistant analyzing LINE group messages.
                TIME HANDLING:
                - When user mentions specific time periods (八月份, 上個月, etc.), MUST use override_start_time and override_end_time
                - Format: 'YYYY-MM-DD HH:MM:SS'
                - Example: "八月份" → override_start_time='2025-08-01 00:00:00', override_end_time='2025-08-31 23:59:59'

                CONTEXT-AWARE FOLLOW-UP QUESTIONS:
                - When user asks follow-up questions, check conversation history for context
                - Extract key entities from previous messages (e.g., names, topics)
                - Use those entities in your search queries

                WORKFLOW:
                1. Check conversation history for context
                2. Use query_messages tool to search for relevant information
                3. Examine the returned results and their scores (0-100)
                4. Make decision based on results:
                - If you have results with score > 30: synthesize answer from those chunks
                - If all scores < 30 or no results: respond that information is not available

                IMPORTANT:
                - Always use the tool BEFORE forming your answer
                - Answer must be in 繁體中文

                Output after using tool:
                {
                    "answer": "your answer or '無法找到問題相關的答案,請再輸入更詳細的資訊'",
                }

                RULES:
                When you CAN answer (have relevant results with score > 30):
                - Combine information from the most relevant chunks
                - Organize the information logically
                - Example: {{"answer": "居服人員的照顧..."}}
                """
        else:
            sys_msg = """You are an intelligent assistant analyzing LINE group messages.
                TIME HANDLING:
                - When user mentions specific time periods (八月份, 上個月, etc.), MUST use override_start_time and override_end_time
                - Format: 'YYYY-MM-DD HH:MM:SS'
                - Example: "八月份" → override_start_time='2025-08-01 00:00:00', override_end_time='2025-08-31 23:59:59'

                CONTEXT-AWARE FOLLOW-UP QUESTIONS:
                - When user asks follow-up questions, check conversation history for context
                - Extract key entities from previous messages (e.g., names, topics)
                - Use those entities in your search queries

                WORKFLOW:
                1. Check conversation history for context
                2. Use query_messages tool to search for relevant information
                3. Examine the returned results and their scores (0-100)
                4. Make decision based on results:
                - If you have results with score > 30: synthesize answer from those chunks
                - If all scores < 30 or no results: respond that information is not available

                IMPORTANT:
                - Always use the tool BEFORE forming your answer
                - Answer must be in 繁體中文

                Output after using tool:
                {
                    "answer": "your answer or '無法找到問題相關的答案,請再輸入更詳細的資訊'",
                    "chunk_ids": "comma-separated chunk_ids OR empty string"
                }

                RULES:
                When you CAN answer (have relevant results with score > 30):
                - Combine information from the most relevant chunks
                - Organize the information logically
                - Include only the chunk_ids you actually referenced
                - Example: {{"answer": "居服人員的照顧...", "chunk_ids": "msg_001,msg_002"}}
                """

        sys_msg = sys_msg + "\n" + time_hint

        try:
            agent = create_agent(
                model=llm_obj,
                tools=tools,
                system_prompt=sys_msg,
                **create_kwargs,
            )
        except Exception as e:
            logger.exception("Failed to create agent: %s", e)
            raise

        try:
            timing_callback = DetailedTimingCallback()

            payload = {
                "messages": [{"role": "user", "content": question}],
            }

            configurable = {
                "configurable": {"thread_id": group_uniid},
                "callbacks": [timing_callback],
            }

            logger.debug(
                "Calling agent.ainvoke: question=%s model=%s thread_id=%s",
                question,
                effective_model,
                group_uniid,
            )

            result = await agent.ainvoke(payload, configurable)

            log_agent_result(result, enabled=True, timing_callback=timing_callback)

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


_default_agent_instance: Optional[LangChainAgent] = None


def get_default_langchain_agent() -> LangChainAgent:
    """獲取全局單例 agent 實例

    配置：
    - use_memory=True: 啟用記憶功能
    - max_messages=5: 保留最近 5 條消息, 設定為 0 表示無限制
    """
    global _default_agent_instance
    if _default_agent_instance is None:
        from app.core.config import settings

        configured_model = getattr(settings, "llm_model", None)
        llm_keep_memory = getattr(settings, "llm_keep_memory", None)
        llm_keep_memory_limit = getattr(settings, "llm_keep_memory_limit", None)

        logger.debug(
            "langchain: llm_model=%s, llm_keep_memory=%s",
            configured_model,
            llm_keep_memory,
        )

        _default_agent_instance = LangChainAgent(
            model=configured_model,
            use_memory=llm_keep_memory,
            max_messages=llm_keep_memory_limit,
        )
    return _default_agent_instance


__all__ = ["LangChainAgent", "get_default_langchain_agent"]
