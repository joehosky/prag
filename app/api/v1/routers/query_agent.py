"""API router exposing the LangChain-based query agent PoC."""

from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.langchain_agent import get_default_langchain_agent
from app.services.query_service import QueryService
from datetime import datetime
from app.core.config import settings

router = APIRouter()


class QueryRequest(BaseModel):
    group_uniid: str
    question: str
    search_type: str = "hybrid"
    top_k: int = 50


class QueryResponse(BaseModel):
    answer: str
    metadata: Optional[Dict] = None


@router.post("/agent", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    question = request.question
    group_uniid = request.group_uniid
    top_k = int(request.top_k or 50)

    try:
        svc = QueryService()
        now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        analysis = svc.analyze_query(question, history=None, now_str=now)
    except Exception:
        analysis = None

    agent = get_default_langchain_agent()

    try:
        start_time = None
        end_time = None
        if analysis:
            start_time = analysis.get("startTime")
            end_time = analysis.get("endTime")

        out = await agent.run(
            question=question,
            group_uniid=group_uniid,
            start_time=start_time,
            end_time=end_time,
            top_k=top_k,
            analysis=analysis,
            use_agent=True,
        )
    except Exception as e:
        return QueryResponse(answer="", confidence=0.0, metadata={"error": str(e)})

    if isinstance(out, dict):
        answer = out.get("answer", "")
        metadata = out.get("metadata")
    else:
        answer = ""
        metadata = {"raw": out}

    return QueryResponse(answer=answer or "", metadata=metadata)
