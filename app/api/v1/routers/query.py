"""
RAG Query Router
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict

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


@router.post("/", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    from app.services.query_service import QueryService

    svc = QueryService()
    try:
        result = await svc.query_group(
            request.group_uniid, request.question, request.top_k, request.search_type
        )
        return QueryResponse(
            answer=result.get("answer", ""),
            confidence=float(result.get("confidence", 0.0)),
            metadata=result.get("metadata"),
        )
    except Exception as e:
        return QueryResponse(answer="", confidence=0.0, metadata={"error": str(e)})
