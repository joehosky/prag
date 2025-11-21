"""LangChain 1.0.x agent runner (strict implementation).

This module provides a single, clean `LangChainAgent` definition and
intentionally does not include fallback logic. It assumes LangChain 1.0.x
APIs are available in the environment.
"""

from __future__ import annotations

import asyncio
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
        "Install them or provide an `llm_instance` when constructing LangChainAgent."
    ) from exc


class LangChainAgent:
    """Strict LangChain 1.0.x agent wrapper.

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
        """Run the LangChain agent and return the agent output."""

        if analysis is None:
            from app.agents.llm_service import analyze_query

            now = (
                __import__("datetime")
                .datetime.now()
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S")
            )
            analysis = analyze_query(question, history=None, now_str=now)

        tools: List[Any] = [query_tool, split_range]

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
            [getattr(t, "__name__", str(t)) for t in tools],
        )

        try:
            agent = create_agent(model=llm_obj, tools=tools, **create_kwargs)
        except Exception as e:
            logger.exception("Failed to create agent: %s", e)
            raise

        ctx = {
            "group_uniid": group_uniid,
            "start_time": start_time,
            "end_time": end_time,
            "top_k": top_k,
            "analysis": analysis,
        }

        # Call agent: prefer `invoke`, then `run`, then callable. Log payload/result for debugging.
        try:
            # Prefer async invocation API if available (langgraph agents expose `ainvoke`)
            if hasattr(agent, "ainvoke"):
                ainvoke_fn = getattr(agent, "ainvoke")
                payload = {"messages": [{"role": "user", "content": question}], **ctx}
                configurable = {"configurable": {"thread_id": group_uniid}}
                logger.debug(
                    "Calling agent.ainvoke payload=%s configurable=%s",
                    payload,
                    configurable,
                )
                out = await ainvoke_fn(payload, configurable)
            elif hasattr(agent, "invoke"):
                invoke_fn = getattr(agent, "invoke")
                payload = {"messages": [{"role": "user", "content": question}], **ctx}
                configurable = {"configurable": {"thread_id": group_uniid}}
                logger.debug(
                    "Calling agent.invoke payload=%s configurable=%s",
                    payload,
                    configurable,
                )
                result = invoke_fn(payload, configurable)
                logger.debug("agent.invoke returned (type=%s)", type(result))
                if inspect.isawaitable(result):
                    out = await result
                else:
                    out = result
            elif hasattr(agent, "run"):
                run_fn = getattr(agent, "run")
                logger.debug("Calling agent.run input=%s context=%s", question, ctx)
                result = run_fn(input=question, context=ctx)
                logger.debug("agent.run returned (type=%s)", type(result))
                if inspect.isawaitable(result):
                    out = await result
                else:
                    out = result
            elif callable(agent):
                logger.debug(
                    "Calling agent callable with input=%s context=%s", question, ctx
                )
                result = agent(input=question, context=ctx)
                logger.debug("callable agent returned (type=%s)", type(result))
                if inspect.isawaitable(result):
                    out = await result
                else:
                    out = result
            else:
                raise RuntimeError("Agent object has no callable/invoke/run method")
        except Exception as exc:
            # Log full context to help debugging tools that behave differently sync/async
            logger.exception(
                "Agent invocation failed. question=%s group_uniid=%s ctx=%s error=%s",
                question,
                group_uniid,
                ctx,
                exc,
            )
            raise

        # Normalize/unwrap agent output into a QueryService-like shape
        answer = ""
        confidence = 0.0
        metadata: Dict[str, Any] = {"raw": {"agent_output": out}}

        candidate = out
        if (
            isinstance(out, dict)
            and "agent_output" in out
            and isinstance(out["agent_output"], dict)
        ):
            candidate = out["agent_output"]

        if isinstance(candidate, dict):
            # Prefer explicit answer/confidence fields
            if candidate.get("answer") or candidate.get("confidence"):
                answer = candidate.get("answer", "")
                try:
                    confidence = float(candidate.get("confidence", 0.0))
                except Exception:
                    confidence = 0.0
                metadata = candidate.get("metadata", metadata)
            else:
                # Try to extract from messages: last AI message content
                msgs = candidate.get("messages") or out.get("messages")
                if msgs:
                    for m in reversed(msgs):
                        content = None
                        if isinstance(m, dict):
                            content = m.get("content")
                        else:
                            content = getattr(m, "content", None)
                        if isinstance(content, str) and content.strip():
                            answer = content
                            try:
                                confidence = float(
                                    candidate.get("raw", {}).get(
                                        "confidence", confidence
                                    )
                                )
                            except Exception:
                                pass
                            break

        result: Dict[str, Any] = {
            "answer": answer or "",
            "confidence": confidence or 0.0,
            "metadata": metadata,
            "agent_output": out,
        }

        return result


__all__ = ["LangChainAgent"]
