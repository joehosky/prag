"""API router exposing the LangChain-based query agent PoC."""

from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Body

from app.agents.langchain_agent import LangChainAgent
from app.agents.llm_service import analyze_query
from datetime import datetime

router = APIRouter()


@router.post("/agent")
async def query_agent(
    payload: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """Call the LangChain agent PoC.

    Expected payload keys: question, group_uniid, start_time (ISO), end_time (ISO), top_k (int), use_agent (bool)
    """
    question = payload.get("question")
    group_uniid = payload.get("group_uniid")
    start_time = payload.get("start_time")
    end_time = payload.get("end_time")
    top_k = int(payload.get("top_k", 50))
    use_agent = bool(payload.get("use_agent", True))

    if not question or not group_uniid:
        return {"error": "question and group_uniid are required"}

    # Produce analysis once at API/Agent layer and pass it down to avoid duplicate LLM calls
    try:
        now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        analysis = analyze_query(question, history=None, now_str=now)
    except Exception:
        analysis = None

    agent = LangChainAgent()
    out = await agent.run(
        question=question,
        group_uniid=group_uniid,
        start_time=start_time,
        end_time=end_time,
        top_k=top_k,
        use_agent=use_agent,
        analysis=analysis,
    )

    return {"result": out}
