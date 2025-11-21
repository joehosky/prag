"""Simple aggregation helper to merge multiple query results.

Performs de-dup by `chunk_id` and sorts by score.
"""

from __future__ import annotations

from typing import List, Dict, Any


def aggregate_results(results_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate a list of tool results into a single structure.

    Each entry in results_list is expected to be a dict with an "items" list,
    where each item has `chunk_id`, `summary`, `score`.
    """
    merged: Dict[str, Dict[str, Any]] = {}
    for res in results_list:
        items = res.get("items", []) if isinstance(res, dict) else []
        for it in items:
            cid = str(it.get("chunk_id"))
            score = float(it.get("score") or 0)
            if cid not in merged or merged[cid].get("score", 0) < score:
                merged[cid] = {
                    "chunk_id": cid,
                    "summary": it.get("summary", ""),
                    "score": score,
                }

    # sort by score desc
    out = sorted(merged.values(), key=lambda x: x.get("score", 0), reverse=True)
    return {"items": out, "count": len(out)}
