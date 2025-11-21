"""Scoring, normalization and MMR utilities for query fusion."""

from __future__ import annotations

import math
from typing import List, Dict, Tuple


def normalize_scores(scores: List[float]) -> List[float]:
    if not scores:
        return []
    mn = min(scores)
    mx = max(scores)
    if mx == mn:
        return [0.5 for _ in scores]
    return [(s - mn) / (mx - mn) for s in scores]


def calculate_recency_boost(days_diff: float, max_boost: float) -> float:
    if days_diff <= 0:
        return max_boost
    if days_diff <= 30:
        return max_boost * (1 - days_diff / 30)
    return 0.0


def fuse_scores(
    q_ids: List[int],
    q_scores: List[float],
    bm_scores: List[float],
    kw_scores: List[float],
    chunks_map: Dict[int, dict],
    alpha: float,
    beta: float,
    gamma: float,
    delta: float,
) -> List[Dict]:
    # normalize each list
    nq = normalize_scores(q_scores)
    nb = normalize_scores(bm_scores)
    nk = normalize_scores(kw_scores)

    score_map: Dict[int, Dict] = {}
    for i, cid in enumerate(q_ids):
        if cid not in score_map:
            score_map[cid] = {"id": cid, "q": 0.0, "b": 0.0, "k": 0.0}
        if i < len(nq):
            score_map[cid]["q"] = nq[i]
        if i < len(nb):
            score_map[cid]["b"] = nb[i]
        if i < len(nk):
            score_map[cid]["k"] = nk[i]

    results: List[Dict] = []
    for cid, sc in score_map.items():
        recency = 0.0
        meta = chunks_map.get(cid)
        if meta and meta.get("start_time"):
            days = meta.get("days_diff", 9999)
            recency = calculate_recency_boost(days, 1.0)
        final = alpha * sc["q"] + beta * sc["b"] + gamma * sc["k"] + delta * recency
        results.append(
            {
                "id": cid,
                "q": sc["q"],
                "b": sc["b"],
                "k": sc["k"],
                "recency": recency,
                "final": final,
            }
        )

    # sort desc
    results.sort(key=lambda x: x["final"], reverse=True)
    return results


def mmr(
    candidates: List[Dict],
    chunk_vectors: Dict[int, List[float]],
    lambd: float,
    top_k: int,
) -> List[Dict]:
    if not candidates:
        return []
    if top_k > len(candidates):
        top_k = len(candidates)
    selected: List[Dict] = []
    remaining = candidates.copy()

    def cosine(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    while len(selected) < top_k and remaining:
        best_idx = -1
        best_score = -1e9
        for i, cand in enumerate(remaining):
            relevance = cand.get("final", 0.0)
            sim_max = 0.0
            vec = chunk_vectors.get(cand["id"])
            if vec and selected:
                for s in selected:
                    svec = chunk_vectors.get(s["id"])
                    if svec:
                        sim = cosine(vec, svec)
                        if sim > sim_max:
                            sim_max = sim
            mmr_score = relevance - lambd * sim_max
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = i
        if best_idx >= 0:
            selected.append(remaining.pop(best_idx))
        else:
            break

    return selected


__all__ = ["normalize_scores", "fuse_scores", "mmr", "calculate_recency_boost"]
