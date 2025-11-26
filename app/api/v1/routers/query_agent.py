"""API router exposing the LangChain-based query agent PoC."""

from __future__ import annotations

from typing import Any, Dict, Optional
from enum import Enum
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.langchain_agent import get_default_langchain_agent
from app.services.query_service import QueryService
from datetime import datetime
from app.core.config import settings

router = APIRouter()


class StreamMode(str, Enum):
    NORMAL = "normal"
    STREAM = "stream"


class QueryRequest(BaseModel):
    group_uniid: str
    question: str
    top_k: int = 50
    stream_mode: StreamMode = StreamMode.NORMAL


class QueryResponse(BaseModel):
    answer: str
    metadata: Optional[Dict] = None


@router.post("/agent")
async def query_agent(request: QueryRequest):
    """Query agent endpoint supporting both normal and streaming modes.

    Args:
        request: QueryRequest with stream_mode to choose response type
            - stream_mode="normal": Returns complete QueryResponse
            - stream_mode="stream": Returns StreamingResponse

    Returns:
        QueryResponse or StreamingResponse based on stream_mode
    """
    question = request.question
    group_uniid = request.group_uniid
    top_k = int(request.top_k or 50)
    stream_mode = request.stream_mode

    # Prepare query analysis
    try:
        svc = QueryService()
        now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        analysis = svc.analyze_query(question, history=None, now_str=now)
    except Exception:
        analysis = None

    start_time = None
    end_time = None
    if analysis:
        start_time = analysis.get("startTime")
        end_time = analysis.get("endTime")

    agent = get_default_langchain_agent()

    # Handle streaming mode
    if stream_mode == StreamMode.STREAM:

        async def event_generator():
            """Generate streaming events"""
            async for chunk in agent.astream(
                question=question,
                group_uniid=group_uniid,
                start_time=start_time,
                end_time=end_time,
                top_k=top_k,
                analysis=analysis,
            ):
                yield chunk

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Handle normal mode
    try:
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
        return QueryResponse(answer="", metadata={"error": str(e)})

    if isinstance(out, dict):
        answer = out.get("answer", "")
        metadata = out.get("metadata")
    else:
        answer = ""
        metadata = {"raw": out}

    return QueryResponse(answer=answer or "", metadata=metadata)
