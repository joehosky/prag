"""Query orchestration: LLM analysis + Qdrant + BM25 + score fusion + MMR."""

from __future__ import annotations

import logging
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import os

from app.agents.llm_service import analyze_query
from app.services.embedding_service import generate_embedding
from app.vector_store.qdrant_client import QdrantService
from qdrant_client.http import models as qmodels
from app.services.bm25_service import BM25Service
from app.repositories.chunk_message_summary_repo import ChunkMessageSummaryRepository
from app.repositories.group_repo import GroupRepository
from app.services.fuse_service import fuse_scores, mmr
from app.db.session import SessionLocal

logger = logging.getLogger("app.services.query_service")


class QueryService:
    async def query_group(
        self,
        group_uniid: str,
        question: str,
        top_k: int = 50,
        search_type: str = "hybrid",
    ) -> Dict[str, Any]:
        gid = None
        db = None
        try:
            db = SessionLocal()
            grp = GroupRepository().get_by_uniid(db, group_uniid)
            if grp:
                gid = int(getattr(grp, "id", gid))
        except Exception:
            logger.exception("Failed to lookup group by uniid %s", group_uniid)
        finally:
            if db:
                try:
                    db.close()
                except Exception:
                    pass

        # 1) LLM analysis
        now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        analysis = analyze_query(question, history=None, now_str=now)
        resolved = analysis.get("resolvedQuery") or question
        keywords = analysis.get("keywords") or []

        # ---- DEBUG INJECTION (temporary) ----
        # Set environment variable DEBUG_QUERY_INJECT=1 to override the LLM
        # analysis with fixed test values for debugging without calling the LLM.
        # PowerShell example: $env:DEBUG_QUERY_INJECT = '1'
        # analysis = {
        #     "queryType": "QueryTypeExact",
        #     "startTime": None,
        #     "endTime": None,
        #     "resolvedQuery": "包聖嬌案主 前測及設備教學回報",
        #     "keywords": [
        #         {"text": "包聖嬌", "required": True},
        #         {"text": "前測", "required": True},
        #         {"text": "設備教學回報", "required": True},
        #     ],
        # }
        # resolved = analysis.get("resolvedQuery")
        # keywords = analysis.get("keywords") or []

        logger.info(
            "query_group:start group_uniid=%s gid=%s resolved=%s keywords=%s",
            group_uniid,
            gid,
            resolved,
            keywords,
        )

        # 2) embedding for query
        try:
            qvec = await asyncio.to_thread(generate_embedding, resolved)
        except Exception:
            logger.exception("Failed to generate embedding for query")
            qvec = None

        # Log query vector summary
        try:
            logger.info(
                "query_group:qvec len=%s",
                len(qvec) if qvec else 0,
            )
        except Exception:
            logger.exception("Failed to log qvec summary")

        # 3) Qdrant search
        qdrant_hits: List[Dict] = []
        try:
            qsvc = QdrantService()
            if qvec:
                qfilter = None
                if gid is not None:
                    try:
                        match_value = int(gid)

                        qfilter = qmodels.Filter(
                            must=[
                                qmodels.FieldCondition(
                                    key="group_id",
                                    match=qmodels.MatchValue(value=match_value),
                                )
                            ]
                        )
                    except Exception:
                        qfilter = None

                res = qsvc.client.search(
                    collection_name=qsvc.collection,
                    query_vector=qvec,
                    limit=top_k,
                    with_payload=True,
                    with_vectors=False,
                    query_filter=qfilter,
                )

                for hit in res:
                    payload = getattr(hit, "payload", None) or {}
                    pid = payload.get("chunk_id")
                    qdrant_hits.append(
                        {"id": pid, "score": float(getattr(hit, "score", 0.0))}
                    )
                logger.info(
                    "query_group:qdrant_search returned %d hits",
                    len(qdrant_hits),
                )
        except Exception:
            logger.exception("Qdrant search failed")
        else:
            if qvec and not qdrant_hits:
                logger.info(
                    "query_group:qdrant_search returned no hits for given vector and filter (gid=%s)",
                    gid,
                )

        # 4) BM25 search
        bm_hits: List[Dict] = []
        try:
            bm = BM25Service()
            pairs = bm.search(resolved, top_k=top_k, group_id=gid)
            logger.info(
                "query_group:bm25 returned %d pairs for group_id=%s",
                len(pairs) if pairs else 0,
                gid,
            )
            for item in pairs:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    doc_id, score = item[0], item[1]
                else:
                    doc_id, score = item, 0.0
                try:
                    bm_hits.append({"id": doc_id, "score": float(score)})
                except Exception:
                    bm_hits.append({"id": doc_id, "score": 0.0})
        except Exception:
            logger.exception("BM25 search failed")
        finally:
            logger.info("query_group:bm25_hits count=%d", len(bm_hits))

        # 5) build candidate set
        candidates = []
        seen = set()
        for h in qdrant_hits:
            if h["id"] and h["id"] not in seen:
                candidates.append(h["id"])
                seen.add(h["id"])
        for h in bm_hits:
            if h["id"] and h["id"] not in seen:
                candidates.append(h["id"])
                seen.add(h["id"])

        # 6) fetch chunk summaries
        db = SessionLocal()
        try:
            repo = ChunkMessageSummaryRepository()
            chunk_map: Dict[int, Dict] = {}
            q_scores = []
            bm_scores = []
            kw_scores = []
            chunk_vectors: Dict[int, List[float]] = {}

            # helper to fetch by chunk_id string
            def fetch_chunk_by_chunk_id(cid: str):
                try:
                    ch = repo.get_by_chunk_id(db, cid)
                    return ch
                except Exception:
                    return None

            # populate scores aligned to candidates
            for cid in candidates:
                ch = fetch_chunk_by_chunk_id(str(cid))
                if not ch:
                    continue

                q_hit = next(
                    (h for h in qdrant_hits if str(h.get("id")) == str(cid)), None
                )
                b_hit = next((h for h in bm_hits if str(h.get("id")) == str(cid)), None)
                q_scores.append(q_hit.get("score") if q_hit else 0.0)
                bm_scores.append(b_hit.get("score") if b_hit else 0.0)

                # keyword score: simple contains count with required boost
                text = ""
                if getattr(ch, "message_summary", None):
                    text = getattr(ch, "message_summary") or ""
                elif getattr(ch, "message_content", None):
                    text = getattr(ch, "message_content") or ""
                low = text.lower() if text else ""
                ks = 0.0
                for k in keywords[:3]:
                    kt = k.get("text", "").strip().lower()
                    if not kt:
                        continue
                    if kt in low:
                        ks += 1.0
                        if k.get("required"):
                            ks += 10.0
                kw_scores.append(ks)

                # recency days
                st = getattr(ch, "start_time", None)
                days = 9999
                if st:
                    try:
                        delta = datetime.now(timezone.utc) - st
                        days = delta.days
                    except Exception:
                        days = 9999

                # vector
                emb = getattr(ch, "embedding", None) or []
                if emb:
                    try:
                        vec = [float(x) for x in emb]
                        chunk_vectors[int(getattr(ch, "id", 0))] = vec
                    except Exception:
                        pass

                chunk_map[int(getattr(ch, "id", 0))] = {
                    "start_time": st,
                    "days_diff": days,
                }

            # align q_ids list as ints for fuse
            q_ids = [int(k) for k in list(chunk_map.keys())]

            logger.debug(
                "query_group:prepared candidates=%d q_ids=%d q_scores_sample=%s bm_scores_sample=%s kw_scores_sample=%s",
                len(candidates),
                len(q_ids),
                q_scores[:10],
                bm_scores[:10],
                kw_scores[:10],
            )

            # 7) fuse
            qtype = analysis.get("queryType", "QueryTypeSemantics")
            if qtype == "QueryTypeSemantics":
                alpha, beta, gamma, delta = 0.50, 0.30, 0.15, 0.05
                lambd = 0.40
                max_results = 12
            elif qtype == "QueryTypeExact":
                alpha, beta, gamma, delta = 0.35, 0.45, 0.15, 0.05
                lambd = 0.20
                max_results = 6
            else:
                alpha, beta, gamma, delta = 0.40, 0.30, 0.10, 0.20
                lambd = 0.30
                max_results = 8

            fused = fuse_scores(
                q_ids,
                q_scores,
                bm_scores,
                kw_scores,
                chunk_map,
                alpha,
                beta,
                gamma,
                delta,
            )
            fused_filtered = [f for f in fused if f.get("final", 0.0) >= 0.3]

            logger.info(
                "query_group:fused count=%d fused_filtered=%d",
                len(fused),
                len(fused_filtered),
            )

            mmr_selected = mmr(
                fused_filtered, chunk_vectors, lambd, min(max_results, top_k)
            )

            mmr_selected = [m for m in mmr_selected if (m.get("final", 0.0) >= 0.3)]

            logger.info(
                "query_group:mmr_selected count=%d items=%s",
                len(mmr_selected),
                mmr_selected,
            )

            # build answer from selected
            results = []
            scores = []
            for item in mmr_selected:
                cid = item.get("id")
                ch = None
                try:
                    if isinstance(cid, int):
                        try:
                            ch = repo.get(db, cid)
                        except Exception:
                            ch = None
                    if not ch:
                        try:
                            ch = repo.get_by_chunk_id(db, str(cid))
                        except Exception:
                            ch = None
                except Exception:
                    ch = None

                text = ""
                if ch:
                    text = getattr(ch, "message_content", None) or getattr(
                        ch, "message_summary", ""
                    )
                results.append(text)
                scores.append(int(round(item.get("final", 0.0) * 100)))

            answer = "\n\n".join(results)
            confidence = max([f.get("final", 0.0) for f in fused_filtered], default=0.0)

            metadata = {
                "analysis": analysis,
                "qdrant_hits": qdrant_hits,
                "bm25_hits": bm_hits,
                "candidates": candidates,
                "scores": scores,
            }

            return {
                "answer": answer,
                "confidence": float(confidence),
                "metadata": metadata,
            }

        finally:
            db.close()


__all__ = ["QueryService"]
