"""
RAG Query Router
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, List

router = APIRouter()


class QueryRequest(BaseModel):
    group_uniid: str
    question: str
    search_type: str = "hybrid"
    top_k: int = 50


class QueryItem(BaseModel):
    chunk_id: str
    score: int
    text: str


class QueryResponse(BaseModel):
    answer: str
    items: List[QueryItem]


@router.post("/", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    from app.services.query_service import QueryService

    svc = QueryService()
    try:
        result = await svc.query_group(
            group_uniid=request.group_uniid,
            question=request.question,
            top_k=request.top_k,
            search_type=request.search_type,
        )
        return QueryResponse(
            answer=result.get("answer", ""), items=result.get("items", [])
        )
    except Exception as e:
        return QueryResponse(answer="", items=[])
