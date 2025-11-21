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

    # Pre-filter chunk ids using DB time-range lookup (if provided)
    allowed_chunk_ids = db_lookup_chunks(group_uniid, start_time, end_time)

    # QueryService.query_group is async; pass through analysis if provided
    result = await svc.query_group(
        group_uniid=group_uniid, question=question, top_k=top_k, analysis=analysis
    )

    # Normalize to expected agent-friendly structure
    items = []
    meta = result.get("metadata", {})
    # metadata.scores and candidates correspond to mmr outputs
    # We use the returned scores and the original candidates to build items
    candidates = meta.get("candidates", [])
    scores = meta.get("scores", [])
    summaries = []
    # The answer is a join of results; split by double newlines to approximate items
    answer = result.get("answer", "")
    if answer:
        summaries = [s.strip() for s in answer.split("\n\n") if s.strip()]

    for idx, cid in enumerate(candidates):
        # If DB prefilter returned ids, skip any candidate not in allowed set
        if allowed_chunk_ids and str(cid) not in set(map(str, allowed_chunk_ids)):
            continue
        items.append(
            {
                "chunk_id": cid,
                "summary": summaries[idx] if idx < len(summaries) else "",
                "score": scores[idx] if idx < len(scores) else 0,
            }
        )

    return {"items": items, "metadata": meta, "raw": result}
