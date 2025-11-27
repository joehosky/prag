"""Query orchestration: LLM analysis + Qdrant + BM25 + score fusion + MMR."""

from __future__ import annotations

import warnings
import logging
import asyncio
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import os
import jieba

import json
from typing import Any, Dict, List, Optional
from app.agents.llm_manager import get_llm_manager

from app.services.embedding_service import agenerate_embedding
from app.vector_store.qdrant_client import QdrantService
from qdrant_client.http import models as qmodels
from app.repositories.chunk_message_summary_repo import ChunkMessageSummaryRepository
from app.repositories.group_repo import GroupRepository
from app.services.fuse_service import fuse_scores, mmr
from app.db.session import SessionLocal
from app.services.bm25_service import get_bm25_service

warnings.filterwarnings("ignore", category=SyntaxWarning, module="jieba")

logger = logging.getLogger("app.services.query_service")


class QueryService:
    MAX_KEYWORDS = 5  # Maximum keywords to extract
    MIN_KEYWORDS = 3  # Minimum keywords needed (triggers TextRank fallback)

    _custom_dict_loaded = False

    def __init__(self):
        self._analysis_cache = {}
        self._embedding_cache: Dict[str, List[float]] = {}  # Cache for embeddings
        self._embedding_cache_max_size = 1000  # Maximum cache entries

        if not QueryService._custom_dict_loaded:
            try:
                custom_dict_path = "data/dict/custom_dict.txt"
                if os.path.exists(custom_dict_path):
                    jieba.load_userdict(custom_dict_path)
                    QueryService._custom_dict_loaded = True
                    logger.info(f"Loaded custom dictionary: {custom_dict_path}")
                else:
                    logger.warning(f"⚠️ Custom dictionary not found: {custom_dict_path}")
            except Exception as e:
                logger.exception(f"❌ Failed to load custom dictionary: {e}")

    async def query_group(
        self,
        group_uniid: str,
        question: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        top_k: int = 50,
        analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        total_start = time.time()
        step_times: Dict[str, float] = {}

        # Step 0: Group lookup
        step_start = time.time()
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
        step_times["group_lookup"] = time.time() - step_start

        # 1) LLM analysis
        step_start = time.time()
        if analysis is None:
            now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
            analysis = self.analyze_query(question, history=None, now_str=now)
            an_start = analysis.get("startTime")
            an_end = analysis.get("endTime")
            if an_start and str(an_start).strip():
                start_time = an_start
            if an_end and str(an_end).strip():
                end_time = an_end
        step_times["llm_analysis"] = time.time() - step_start

        resolved = analysis.get("resolvedQuery")
        keywords = analysis.get("keywords") or []
        queryType = analysis.get("queryType", "QueryTypeExact")

        logger.debug(
            "query_group: group_uniid=%s intent=%s gid=%s resolved=%s keywords=%s start_time=%s end_time=%s",
            group_uniid,
            queryType,
            gid,
            resolved,
            keywords,
            start_time,
            end_time,
        )

        # 2) embedding for query with caching
        step_start = time.time()
        qvec = None
        cache_key = resolved.strip().lower()  # Normalize for cache key

        # Check cache first
        if cache_key in self._embedding_cache:
            qvec = self._embedding_cache[cache_key]
            logger.debug("Embedding cache hit for query: %s", resolved[:50])
        else:
            try:
                # Use native async function instead of wrapping sync in thread
                qvec = await agenerate_embedding(resolved)

                # Store in cache (with size limit)
                if len(self._embedding_cache) >= self._embedding_cache_max_size:
                    # Remove oldest entry (simple FIFO)
                    self._embedding_cache.pop(next(iter(self._embedding_cache)))
                self._embedding_cache[cache_key] = qvec
                logger.debug("Embedding cached for query: %s", resolved[:50])
            except Exception:
                logger.exception("Failed to generate embedding for query")

        step_times["embedding"] = time.time() - step_start

        logger.debug(
            "query_group:qvec len=%s",
            len(qvec) if qvec else 0,
        )

        # 3) Qdrant search
        step_start = time.time()
        qdrant_hits: List[Dict] = []
        try:
            qsvc = QdrantService()
            if qvec:
                must_filters = []

                # group id filter
                if gid is not None:
                    must_filters.append(
                        {"key": "group_id", "match": {"value": int(gid)}}
                    )

                if (start_time and str(start_time).strip()) or (
                    end_time and str(end_time).strip()
                ):
                    time_filter = {"key": "date", "range": {}}

                    if start_time and str(start_time).strip():
                        time_filter["range"]["gte"] = (
                            str(start_time).strip().split(" ")[0]
                        )

                    if end_time and str(end_time).strip():
                        time_filter["range"]["lte"] = (
                            str(end_time).strip().split(" ")[0]
                        )

                    must_filters.append(time_filter)

                    logger.debug("Building date range filter: %s", time_filter)

                query_filter = None
                if must_filters:
                    query_filter = {"must": must_filters}

                logger.debug("Qdrant filter: %s", query_filter)

                res = qsvc.client.search(
                    collection_name=qsvc.collection,
                    query_vector=qvec,
                    limit=top_k,
                    with_payload=True,
                    with_vectors=False,
                    query_filter=query_filter,
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
                logger.debug(
                    "query_group:qdrant_search returned no hits for given vector and filter (gid=%s)",
                    gid,
                )
        step_times["qdrant_search"] = time.time() - step_start

        # 4) BM25 search
        step_start = time.time()
        bm_hits: List[Dict] = []
        try:
            bm = get_bm25_service()
            pairs = bm.search(resolved, top_k=top_k, group_id=gid)
            logger.debug(
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
            logger.debug("query_group:bm25_hits count=%d", len(bm_hits))
        step_times["bm25_search"] = time.time() - step_start

        # 5) build candidate set
        step_start = time.time()
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
        step_times["build_candidates"] = time.time() - step_start

        # 6) fetch chunk summaries
        step_start = time.time()
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
            step_times["fetch_chunks"] = time.time() - step_start

            logger.info(
                "query_group:prepared candidates=%d q_ids=%d q_scores_sample=%s bm_scores_sample=%s kw_scores_sample=%s",
                len(candidates),
                len(q_ids),
                q_scores[:10],
                bm_scores[:10],
                kw_scores[:10],
            )

            # 7) fuse
            step_start = time.time()
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
            step_times["fuse_scores"] = time.time() - step_start

            logger.info(
                "query_group:fused count=%d fused_filtered=%d",
                len(fused),
                len(fused_filtered),
            )

            # 8) MMR
            step_start = time.time()
            mmr_selected = mmr(
                fused_filtered, chunk_vectors, lambd, min(max_results, top_k)
            )

            mmr_selected = [m for m in mmr_selected if (m.get("final", 0.0) >= 0.3)]
            step_times["mmr"] = time.time() - step_start

            logger.debug(
                "query_group:mmr_selected count=%d items=%s",
                len(mmr_selected),
                mmr_selected,
            )

            # 9) build answer
            step_start = time.time()
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
            step_times["build_answer"] = time.time() - step_start

            # Log timing summary
            total_elapsed = time.time() - total_start
            logger.info(
                "query_group:timing total=%.2fs | llm_analysis=%.2fs | embedding=%.2fs | qdrant=%.2fs | bm25=%.2fs | fetch_chunks=%.2fs | fuse=%.2fs | mmr=%.2fs | build_answer=%.2fs",
                total_elapsed,
                step_times.get("llm_analysis", 0),
                step_times.get("embedding", 0),
                step_times.get("qdrant_search", 0),
                step_times.get("bm25_search", 0),
                step_times.get("fetch_chunks", 0),
                step_times.get("fuse_scores", 0),
                step_times.get("mmr", 0),
                step_times.get("build_answer", 0),
            )

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
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze the user's question with fast path optimization."""
        step_start = time.time()

        time_keywords = [
            "今天",
            "昨天",
            "今日",
            "昨日",
            "明天",
            "這周",
            "上周",
            "本周",
            "上週",
            "下周",
            "這個月",
            "上個月",
            "本月",
            "上月",
            "下個月",
            "這一周",
            "上一周",
            "這星期",
            "上星期",
            "最近",
            "近期",
            "前天",
            "大前天",
            "後天",
            "今年",
            "去年",
            "明年",
            "today",
            "yesterday",
            "tomorrow",
            "this week",
            "last week",
            "next week",
        ]

        has_time_keyword = any(kw in question.lower() for kw in time_keywords)

        if not has_time_keyword and not history:
            elapsed = time.time() - step_start
            logger.debug(
                "analyze_query: fast path (no time keywords, no history) in %.3fs",
                elapsed,
            )
            return self._analyze_query_fast(question)

        logger.debug(
            "analyze_query: full LLM path (time_keywords=%s, has_history=%s)",
            has_time_keyword,
            bool(history),
        )
        return self._analyze_query_full(question, history, now_str, model)

    def _analyze_query_fast(self, question: str) -> Dict[str, Any]:
        """Fast query analysis without LLM."""
        logger.debug("Run Fast analysis")

        try:
            import jieba.posseg as pseg

            # Global stop words
            global_stop_words = {
                "什麼",
                "哪個",
                "哪些",
                "怎麼",
                "為何",
                "為什麼",
                "如何",
                "是否",
                "已經",
                "還",
                "也",
                "都",
                "再",
                "又",
                "就",
                "才",
                "這",
                "那",
                "這個",
                "那個",
                "這些",
                "那些",
                "在",
                "於",
                "對",
                "對於",
                "關於",
                "由於",
                "是",
                "有",
                "會",
                "能",
                "可以",
                "應該",
                "嗎",
                "呢",
                "吧",
                "啊",
                "的",
                "了",
                "過",
                "東西",
                "事情",
                "時候",
                "地方",
                "方面",
                "情況",
                "提供",
                "進行",
                "完成",
                "開始",
                "結束",
                "需要",
                "多少",
                "幾個",
                "哪些",
            }

            # 1. POS tagging analysis
            words = list(pseg.cut(question))

            word_details = [(w.word, w.flag) for w in words]
            logger.debug(f"Segmentation: {word_details}")

            def is_valid_keyword(word: str, min_len: int = 2) -> bool:
                """Check if word is valid keyword"""
                return (
                    word not in global_stop_words
                    and len(word) >= min_len
                    and not word.isdigit()
                )

            # 2. Collect candidate keywords
            candidates = []

            # Phase 1: Extract entities first
            entities = [
                w.word
                for w in words
                if w.flag in ["nr", "ns", "nt", "nz"] and is_valid_keyword(w.word)
            ]
            candidates.extend(entities)
            logger.debug(f"Entities: {entities}")

            # Phase 2: Add nouns if needed
            if len(candidates) < self.MAX_KEYWORDS:
                nouns = [
                    w.word
                    for w in words
                    if w.flag in ["n", "vn"] and is_valid_keyword(w.word)
                ]
                nouns.sort(key=len, reverse=True)
                candidates.extend(nouns)
                logger.debug(f"Nouns: {nouns}")

            # Phase 3: Add verbs (stricter filtering)
            if len(candidates) < self.MAX_KEYWORDS:
                verbs = [
                    w.word for w in words if w.flag == "v" and is_valid_keyword(w.word)
                ]
                # Filter common generic verbs
                common_verbs = {
                    "做",
                    "弄",
                    "搞",
                    "去",
                    "來",
                    "說",
                    "講",
                    "看",
                    "提供",
                    "進行",
                    "開始",
                    "結束",
                    "完成",
                }
                verbs = [v for v in verbs if v not in common_verbs]
                candidates.extend(verbs)
                logger.debug(f"Verbs: {verbs}")

            # 3. Deduplicate while preserving order
            seen = set()
            keywords_list = []
            for word in candidates:
                if word not in seen:
                    keywords_list.append(word)
                    seen.add(word)
                    if len(keywords_list) >= self.MAX_KEYWORDS:
                        break

            # 4. TextRank fallback
            if len(keywords_list) < self.MIN_KEYWORDS:
                import jieba.analyse

                raw_keywords = jieba.analyse.textrank(
                    question, topK=self.MAX_KEYWORDS, withWeight=False
                )
                for kw in raw_keywords:
                    if is_valid_keyword(kw) and kw not in seen:
                        keywords_list.append(kw)
                        seen.add(kw)
                        if len(keywords_list) >= self.MAX_KEYWORDS:
                            break

            # Determine query type
            has_person = any(w.flag == "nr" for w in words)
            has_org = any(w.flag in ["nt", "nz"] for w in words)
            entity_indicators = ["誰", "哪位", "什麼人"]
            has_entity_indicator = any(ind in question for ind in entity_indicators)

            query_type = (
                "QueryTypeExact"
                if (has_person or has_org or has_entity_indicator)
                else "QueryTypeSemantics"
            )

            keywords = [{"text": kw, "required": True} for kw in keywords_list]

            logger.debug(
                "Fast analysis: type=%s, keywords=%s",
                query_type,
                [k["text"] for k in keywords],
            )

            return {
                "queryType": query_type,
                "startTime": None,
                "endTime": None,
                "resolvedQuery": question,
                "keywords": keywords,
            }
        except Exception:
            logger.exception("Fast analysis failed, using default")
            return self._default_analysis(question)

    def _analyze_query_full(
        self,
        question: str,
        history: Optional[List[Dict[str, Any]]] = None,
        now_str: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Full query analysis with LLM (for queries with time keywords or history)."""
        step_start = time.time()

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

        prompt = f"""分析查詢並輸出 JSON。當前：{now_str}
                    問題：{question}
                    {f"上下文：{ctx_text}" if ctx_text else ""}

                    輸出：{{"queryType":"QueryTypeSemantics|QueryTypeExact|QueryTypeRecent","startTime":"YYYY-MM-DD HH:MM:SS或null","endTime":"YYYY-MM-DD HH:MM:SS或null","resolvedQuery":"改寫查詢","keywords":[{{"text":"詞","required":true/false}}]}}

                    規則：
                    - Exact：人名/公司/產品/日期/編號
                    - Recent：今天/昨天/最近/這周（≤30天）
                    - Semantics：其他

                    時間：今天→當日｜昨天→前日｜這周→本周一至日｜最近→7天前至今｜無→null

                    改寫：替換代詞、移除時間詞、保留關鍵詞
                    關鍵詞：最多3個
                    純JSON，無markdown。"""

        try:
            llm_manager = get_llm_manager()
            if model:
                try:
                    raw = llm_manager.invoke(prompt, max_tokens=512, model=model)
                except TypeError:
                    raw = llm_manager.invoke(prompt, max_tokens=512)
            else:
                raw = llm_manager.invoke(prompt, max_tokens=512)

            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            parsed = json.loads(raw)

            elapsed = time.time() - step_start
            logger.debug("analyze_query: full LLM completed in %.2fs", elapsed)

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
