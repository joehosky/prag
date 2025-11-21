"""Thin wrapper tool that calls existing QueryService.query_group.

This returns a structured dict suitable for agent consumption.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime

from app.services.query_service import QueryService
from app.tools.db_lookup_tool import db_lookup_chunks


async def query_tool(
    question: str,
    group_uniid: str,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    top_k: int = 50,
    analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Call QueryService.query_group and normalize output.

    start_time / end_time are accepted for tool signature and used to
    pre-filter chunk ids via DB lookup. If `analysis` is provided it will
    be passed through to QueryService to avoid redundant LLM calls.
    """
    svc = QueryService()

    result = await svc.query_group(
        group_uniid=group_uniid, question=question, top_k=top_k, analysis=analysis
    )

    items = []
    meta = result.get("metadata", {})
    candidates = meta.get("candidates", [])
    scores = meta.get("scores", [])
    summaries = []

    answer = result.get("answer", "")
    if answer:
        summaries = [s.strip() for s in answer.split("\n\n") if s.strip()]

    for idx, cid in enumerate(candidates):
        items.append(
            {
                "chunk_id": cid,
                "summary": summaries[idx] if idx < len(summaries) else "",
                "score": scores[idx] if idx < len(scores) else 0,
            }
        )

    return {"items": items, "metadata": meta, "raw": result}
