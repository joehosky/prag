"""API router exposing the LangChain-based query agent PoC."""

from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.langchain_agent import LangChainAgent
from app.agents.llm_service import analyze_query
from datetime import datetime

router = APIRouter()


class QueryRequest(BaseModel):
    group_uniid: str
    question: str
    search_type: str = "hybrid"
    top_k: int = 50


class QueryResponse(BaseModel):
    answer: str
    confidence: float
    metadata: Optional[Dict] = None


@router.post("/agent", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """Call the LangChain agent PoC"""
    question = request.question
    group_uniid = request.group_uniid
    top_k = int(request.top_k or 50)

    try:
        now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        analysis = analyze_query(question, history=None, now_str=now)
    except Exception:
        analysis = None

    agent = LangChainAgent()
    try:
        start_time = None
        end_time = None
        if analysis:
            try:
                start_time = analysis.get("startTime")
            except Exception:
                start_time = None
            try:
                end_time = analysis.get("endTime")
            except Exception:
                end_time = None

        out = await agent.run(
            question=question,
            group_uniid=group_uniid,
            start_time=start_time,
            end_time=end_time,
            top_k=top_k,
            use_agent=True,
            analysis=analysis,
        )
    except Exception as e:
        return QueryResponse(answer="", confidence=0.0, metadata={"error": str(e)})

    answer = ""
    confidence = 0.0
    metadata: Dict[str, Any] = {"raw": out}

    if isinstance(out, dict):
        # If agent returned a QueryService-like dict
        # Also support agents that return their result under an `agent_output` key
        candidate = out
        if "agent_output" in out and isinstance(out["agent_output"], dict):
            candidate = out["agent_output"]

        if candidate.get("answer") or candidate.get("confidence"):
            answer = candidate.get("answer", "")
            confidence = float(candidate.get("confidence", 0.0))
            metadata = candidate.get("metadata", out.get("metadata", metadata))
        else:
            # If candidate contains agent-style messages (langchain AIMessage objects or dicts),
            # try to extract the last AI message content as the answer.
            msgs = candidate.get("messages") if isinstance(candidate, dict) else None
            if not msgs and isinstance(out, dict):
                msgs = out.get("messages")

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
                                candidate.get("raw", {}).get("confidence", confidence)
                            )
                        except Exception:
                            pass
                        break

    return QueryResponse(
        answer=answer or "", confidence=confidence or 0.0, metadata=metadata
    )
