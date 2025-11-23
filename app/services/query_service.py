"""Query orchestration: LLM analysis + Qdrant + BM25 + score fusion + MMR."""

from __future__ import annotations

import logging
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import os

import json
from typing import Any, Dict, List, Optional
from app.agents.llm_manager import get_llm_manager

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
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        top_k: int = 50,
        search_type: str = "hybrid",
        analysis: Optional[Dict[str, Any]] = None,
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
        if analysis is None:
            now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
            analysis = self.analyze_query(question, history=None, now_str=now)
            an_start = analysis.get("startTime")
            an_end = analysis.get("endTime")
            if an_start and str(an_start).strip():
                start_time = an_start
            if an_end and str(an_end).strip():
                end_time = an_end

        resolved = analysis.get("resolvedQuery")
        keywords = analysis.get("keywords") or []

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
                try:
                    must_filters = []
                    # group id filter
                    if gid is not None:
                        try:
                            match_value = int(gid)
                            must_filters.append(
                                qmodels.FieldCondition(
                                    key="group_id",
                                    match=qmodels.MatchValue(value=match_value),
                                )
                            )
                        except Exception:
                            logger.debug("query_group: invalid gid for filter: %s", gid)

                    # date range filter: use only date portion (YYYY-MM-DD)
                    try:
                        if (start_time and str(start_time).strip()) or (
                            end_time and str(end_time).strip()
                        ):
                            gte = None
                            lte = None
                            if start_time and str(start_time).strip():
                                try:
                                    gte = str(start_time).strip().split(" ")[0]
                                except Exception:
                                    gte = str(start_time).strip()
                            if end_time and str(end_time).strip():
                                try:
                                    lte = str(end_time).strip().split(" ")[0]
                                except Exception:
                                    lte = str(end_time).strip()

                            # build range only with provided bounds
                            range_kwargs = {}
                            if gte is not None:
                                range_kwargs["gte"] = gte
                            if lte is not None:
                                range_kwargs["lte"] = lte

                            if range_kwargs:
                                must_filters.append(
                                    qmodels.FieldCondition(
                                        key="date",
                                        range=qmodels.Range(**range_kwargs),
                                    )
                                )
                    except Exception:
                        logger.exception("Failed to build date range filter")

                    if must_filters:
                        qfilter = qmodels.Filter(must=must_filters)
                    else:
                        qfilter = None
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

            # apply optional date-range filtering to BM25 hits using chunk start_time
            if (start_time and str(start_time).strip()) or (
                end_time and str(end_time).strip()
            ):
                db_tmp = None
                try:
                    ids = [str(h.get("id")) for h in bm_hits if h.get("id")]
                    if not ids:
                        bm_hits = []
                    else:
                        db_tmp = SessionLocal()
                        repo_tmp = ChunkMessageSummaryRepository()
                        chunks = repo_tmp.get_by_chunk_ids(db_tmp, ids)
                        chunk_map_by_chunk_id = {
                            str(getattr(c, "chunk_id")): c for c in chunks
                        }

                        def _parse_date_only(s: str):
                            s2 = str(s).strip().split(" ")[0]
                            try:
                                return datetime.strptime(s2, "%Y-%m-%d").date()
                            except Exception:
                                return None

                        gte_date = (
                            _parse_date_only(start_time)
                            if start_time and str(start_time).strip()
                            else None
                        )
                        lte_date = (
                            _parse_date_only(end_time)
                            if end_time and str(end_time).strip()
                            else None
                        )

                        filtered = []
                        for h in bm_hits:
                            cid = h.get("id")
                            if cid is None:
                                continue
                            ch = chunk_map_by_chunk_id.get(str(cid))
                            if not ch:
                                continue
                            st = getattr(ch, "start_time", None)
                            if not st:
                                continue
                            try:
                                ch_date = st.date()
                            except Exception:
                                continue
                            ok = True
                            if gte_date and ch_date < gte_date:
                                ok = False
                            if lte_date and ch_date > lte_date:
                                ok = False
                            if ok:
                                filtered.append(h)

                        bm_hits = filtered
                except Exception:
                    logger.exception("Failed to filter BM25 hits by date range (batch)")
                finally:
                    if db_tmp:
                        try:
                            db_tmp.close()
                        except Exception:
                            pass
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

            logger.debug(
                "query_group:mmr_selected count=%d items=%s",
                len(mmr_selected),
                mmr_selected,
            )

            # build answer from selected: create items list with chunk_id, score and text
            items = []
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
                chunk_id = ""
                if ch:
                    text = getattr(ch, "message_content", None) or getattr(
                        ch, "message_summary", ""
                    )
                    chunk_id = getattr(ch, "chunk_id", "")

                score_int = int(round(item.get("final", 0.0) * 100))
                items.append({"chunk_id": chunk_id, "score": score_int, "text": text})

            answer = "\n\n".join([it.get("text", "") for it in items])

            # Return only answer and per-item chunk_id/score/text to simplify caller parsing
            return {"answer": answer, "items": items}

        finally:
            db.close()

    def _default_analysis(self, question: str) -> Dict[str, Any]:
        return {
            "queryType": "general",
            "startTime": None,
            "endTime": None,
            "resolvedQuery": question,
            "keywords": [],
        }

    def analyze_query(
        self,
        question: str,
        history: Optional[List[Dict[str, Any]]] = None,
        now_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze the user's question using the LLM manager.

        This function was moved from `app.agents.llm_service` into the services
        layer so analysis logic lives with other query orchestration code.
        """

        ctx_text = ""
        if history:
            try:
                parts = []
                for h in history:
                    if isinstance(h, dict):
                        parts.append(h.get("content") or h.get("text") or str(h))
                    else:
                        parts.append(str(h))
                ctx_text = "\n".join([p for p in parts if p])
            except Exception:
                ctx_text = str(history)

        prompt = f"""
                分析查詢並輸出 JSON。當前時間：{now_str}

                問題：{question}
                歷史對話：{ctx_text}

                輸出格式：
                {{"queryType":"QueryTypeSemantics|QueryTypeExact|QueryTypeRecent","startTime":"YYYY-MM-DD HH:MM:SS或null","endTime":"YYYY-MM-DD HH:MM:SS或null","resolvedQuery":"改寫查詢","keywords":[{{"text":"詞","required":true/false}}]}}

                queryType 規則：
                - QueryTypeExact：有人名/公司名/產品名/明確日期/特定編號
                - QueryTypeRecent：有"今天/昨天/最近/這周"等時間詞，或範圍≤30天
                - QueryTypeSemantics：其他情況
                優先級：Exact > Recent > Semantics

                時間轉換（台北時區，周一為首日）：
                今天→00:00-23:59｜昨天→前一天｜這周→周一至周日｜上周→上周一至周日｜這個月→1日至月底｜最近→7天前至今｜無時間詞→null

                改寫規則（重要）：
                1. 必須從歷史對話提取實體替換代詞（他/她/它/這個/那個/第一個/也/還等）
                2. 移除時間詞（已在 startTime/endTime）
                3. 保留核心關鍵詞
                4. 如果問題中有代詞，必須從歷史找到對應實體

                關鍵詞：最多3個，實體required=true、屬性false、無則[]

                純JSON輸出，無markdown。
                """

        try:
            llm_manager = get_llm_manager()
            raw = llm_manager.invoke(prompt, max_tokens=1024)

            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            parsed = json.loads(raw)
            return {
                "queryType": parsed.get("queryType") or "general",
                "startTime": parsed.get("startTime"),
                "endTime": parsed.get("endTime"),
                "resolvedQuery": parsed.get("resolvedQuery") or question,
                "keywords": parsed.get("keywords") or [],
            }
        except Exception:
            logger.exception("LLM analysis failed, using default")
            return self._default_analysis(question)


__all__ = ["QueryService"]
