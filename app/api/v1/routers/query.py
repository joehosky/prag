"""
RAG Query Router
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, List

from app.tools.query_tool import query_messages_tool

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
    try:
        tool = query_messages_tool(
            group_uniid=request.group_uniid,
            top_k=request.top_k,
        )

        result = await tool.ainvoke(request.question)

        return QueryResponse(
            answer=result.get("answer", ""), items=result.get("items", [])
        )
    except Exception as e:
        return QueryResponse(answer="", items=[])
