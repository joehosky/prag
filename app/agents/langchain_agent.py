"""LangChain 1.0.x agent PoC runner.

This PoC tries to use LangChain's `create_agent` when available. For
reliability in environments without the exact LangChain API, a simple
fallback orchestrator is provided that uses the tools implemented under
`app.tools`.

This module implements an async `run` function that returns aggregated
results for a user query.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.tools.query_tool import query_tool
from app.tools.split_range_tool import split_range
from app.tools.aggregate_tool import aggregate_results

logger = logging.getLogger("app.agents.langchain_agent")


class LangChainAgent:
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        max_steps: int = 6,
        max_span_days: int = 7,
    ) -> None:
        self.model = model
        self.max_steps = max_steps
        self.max_span_days = max_span_days

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
        """Run agent PoC. If LangChain 1.0.x is available it will attempt to
        construct an agent; otherwise fallback to simple orchestrator.
        """
        # Try to import LangChain create_agent API (best-effort)
        try:
            from langchain.agents import create_agent  # type: ignore
            from langchain.memory import MemorySaver  # type: ignore
        except Exception:
            create_agent = None
            MemorySaver = None

        # If caller didn't provide an analysis dict, attempt to produce one
        if analysis is None:
            try:
                from app.agents.llm_service import analyze_query

                now = (
                    __import__("datetime")
                    .datetime.now()
                    .astimezone()
                    .strftime("%Y-%m-%d %H:%M:%S")
                )
                analysis = analyze_query(question, history=None, now_str=now)
            except Exception:
                analysis = None

        if use_agent and create_agent:
            try:
                # Build simple tool wrappers for LangChain
                # Note: create_agent usage varies by LangChain version; we
                # pass model name and callable tools as a simple PoC.
                tools = [
                    {
                        "name": "query_tool",
                        "func": query_tool,
                        "description": "Run retrieval for a question and group_uniid",
                    },
                    {
                        "name": "split_range",
                        "func": split_range,
                        "description": "Split a date range into windows",
                    },
                ]

                # Pass analysis in the agent context so tools/agent can use it
                agent = create_agent(model=self.model, tools=tools)

                # run agent in an async context if supported
                if asyncio.iscoroutinefunction(agent.run):
                    out = await agent.run(
                        input=question,
                        context={
                            "group_uniid": group_uniid,
                            "start_time": start_time,
                            "end_time": end_time,
                            "top_k": top_k,
                            "analysis": analysis,
                        },
                    )
                else:
                    # sync fallback
                    loop = asyncio.get_running_loop()
                    out = await loop.run_in_executor(None, lambda: agent.run(question))

                return {"agent_output": out}
            except Exception:
                logger.exception("LangChain agent failed; falling back to orchestrator")

        # Fallback simple orchestrator: if time range is provided and large,
        # split into windows and call query_tool for each window in parallel.
        # Determine windows: prefer analysis start/end if present
        use_start = start_time
        use_end = end_time
        if analysis:
            use_start = analysis.get("startTime") or use_start
            use_end = analysis.get("endTime") or use_end

        if use_start and use_end:
            windows = split_range(use_start, use_end, max_span_days=self.max_span_days)
        else:
            windows = [(use_start, use_end)]

        results: List[Dict[str, Any]] = []
        sem = asyncio.Semaphore(self.max_steps)

        async def _call_window(q, g, s, e):
            async with sem:
                # Note: query_tool ignores start/end for now; kept for future
                return await query_tool(
                    q, g, start_time=s, end_time=e, top_k=top_k, analysis=analysis
                )

        tasks = [
            asyncio.create_task(_call_window(question, group_uniid, s, e))
            for s, e in windows
        ]
        # limit number of concurrent tasks
        try:
            res = await asyncio.gather(*tasks)
        except Exception:
            # if any fails, collect completed
            res = [t.result() for t in tasks if t.done()]

        results.extend(res)

        aggregated = aggregate_results(results)

        return {
            "items": aggregated.get("items", []),
            "count": aggregated.get("count", 0),
            "windows": windows,
        }


__all__ = ["LangChainAgent"]
