"""LangChain 1.0.x agent runner

This module provides a single, clean `LangChainAgent` definition with
proper parameter binding to tools.
"""

from __future__ import annotations

import inspect
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.tools.query_tool import query_tool
from app.tools.split_range_tool import split_range

logger = logging.getLogger("app.agents.langchain_agent")

try:
    from langchain.agents import create_agent
    from langchain_openai import ChatOpenAI
    from langgraph.checkpoint.memory import InMemorySaver
except Exception as exc:
    raise ImportError(
        "langchain 1.0.x and provider packages (langchain_openai, langgraph) are required for LangChainAgent.\n"
    ) from exc


class LangChainAgent:
    """Strict LangChain 1.0.x agent wrapper with proper tool parameter binding.

    Parameters
    - model: model name passed to LangChain's OpenAI when no `llm_instance` is provided.
    - llm_instance: optional pre-initialized LLM object (preferred).
    - use_memory: attach MemorySaver when True.
    - agent_kwargs: forwarded to `create_agent`.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        llm_instance: Optional[Any] = None,
        use_memory: bool = False,
        agent_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.model = model
        self.llm_instance = llm_instance
        self.use_memory = use_memory
        self.agent_kwargs = agent_kwargs or {}

    async def run(
        self,
        question: str,
        group_uniid: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        top_k: int = 50,
        use_agent: bool = True,
        analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run the LangChain agent and return the agent output.

        This method creates dynamically bound tools that capture the context
        parameters (group_uniid, start_time, end_time, top_k, analysis) so
        the LLM only needs to provide the question parameter when calling tools.
        """

        if analysis is None:
            from app.agents.llm_service import analyze_query

            now = (
                __import__("datetime")
                .datetime.now()
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S")
            )
            analysis = analyze_query(question, history=None, now_str=now)

        try:
            from langchain_core.tools import tool
        except ImportError:
            from langchain.tools import tool

        @tool
        async def query_messages(question_text: str) -> Dict[str, Any]:
            """Search and retrieve relevant LINE messages based on the question.

            This tool searches through the LINE group's message history to find
            relevant messages that match the given question or search query.

            Args:
                question_text: The search query or question to find relevant messages.
                             This should be a natural language question or keywords.

            Returns:
                A dictionary containing:
                - items: List of matched messages with chunk_id, summary, and score
                - metadata: Additional information about the search
                - raw: Raw query service results
            """
            return await query_tool(
                question=question_text,
                group_uniid=group_uniid,
                start_time=start_time,
                end_time=end_time,
                top_k=top_k,
                analysis=analysis,
            )

        tools: List[Any] = [query_messages, split_range]

        if self.llm_instance is not None:
            llm_obj = self.llm_instance
        else:
            if not settings.openai_api_key:
                raise RuntimeError(
                    "OpenAI API key not configured in settings.openai_api_key"
                )
            llm_obj = ChatOpenAI(
                model=self.model, openai_api_key=settings.openai_api_key
            )

        checkpointer = InMemorySaver() if self.use_memory else None

        create_kwargs = dict(self.agent_kwargs)
        if checkpointer is not None:
            create_kwargs["checkpointer"] = checkpointer

        logger.debug(
            "Creating agent: model=%s use_memory=%s agent_kwargs=%s tools=%s",
            self.model,
            self.use_memory,
            create_kwargs,
            [getattr(t, "name", getattr(t, "__name__", str(t))) for t in tools],
        )

        try:
            agent = create_agent(model=llm_obj, tools=tools, **create_kwargs)
        except Exception as e:
            logger.exception("Failed to create agent: %s", e)
            raise

        try:
            sys_msg = (
                f"You are helping search LINE group messages for group {group_uniid}. "
            )
            sys_msg += (
                "Use the query_messages tool to search for relevant messages based on the user's question. "
                "The tool requires only the search question - all other context is already configured."
            )

            payload = {
                "messages": [
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": question},
                ],
            }
            configurable = {"configurable": {"thread_id": group_uniid}}

            result = await agent.ainvoke(payload, configurable)
            logger.debug("agent.ainvoke returned (type=%s)", type(result))

            out = result

            # Expect agent to return canonical content dict in the last message:
            # {'answer': str, 'items': [{chunk_id, score, text}, ...]}
            msgs = out["messages"]
            last = msgs[-1]
            candidate = last["content"]

        except Exception as exc:
            logger.exception(
                "Agent invocation failed. question=%s group_uniid=%s error=%s",
                question,
                group_uniid,
                exc,
            )
            raise

        # Normalize agent output according to new query_tool / QueryService format
        answer = ""
        confidence = 0.0
        metadata: Dict[str, Any] = {}

        answer = candidate.get("answer", "") or ""
        items = candidate.get("items") or []

        # compute confidence from items' scores (scores are integers 0-100)
        try:
            if items:
                max_score = max([int(i.get("score", 0)) for i in items])
                confidence = float(max_score) / 100.0
            else:
                confidence = 0.0
        except Exception:
            confidence = 0.0

        metadata["items"] = items

        result: Dict[str, Any] = {
            "answer": answer or "",
            "confidence": confidence or 0.0,
            "metadata": metadata,
        }

        return result


__all__ = ["LangChainAgent"]
