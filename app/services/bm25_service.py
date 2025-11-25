from __future__ import annotations

import os
import pickle
import logging
import threading
from typing import Dict, Tuple, List, Any, Set
from datetime import datetime

from rank_bm25 import BM25Okapi

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.chunk_message_summary_repo import (
    ChunkMessageSummaryRepository,
)
from app.db.session import SessionLocal


_global_bm25_instance: "BM25Service" | None = None
_global_bm25_lock = threading.Lock()


def get_bm25_service() -> "BM25Service":
    """Get or create global BM25 service instance (singleton pattern)"""
    global _global_bm25_instance

    if _global_bm25_instance is None:
        with _global_bm25_lock:
            if _global_bm25_instance is None:
                import time

                start = time.time()
                _global_bm25_instance = BM25Service()
                elapsed = time.time() - start
                logger.info(
                    "Global BM25 service initialized: %d docs loaded in %.2fs",
                    len(_global_bm25_instance.docs),
                    elapsed,
                )

    return _global_bm25_instance


def _parse_datetime(value: str) -> datetime:
    """Parse common datetime string formats into a timezone-naive datetime."""
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except Exception:
        pass
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except Exception:
        raise


logger = logging.getLogger(__name__)


def _tokenize(text: str) -> List[str]:
    """Tokenizer that prefers jieba for Chinese text."""
    try:
        import jieba

        tokens = [t for t in jieba.cut(text) if t and t.strip()]
        return tokens
    except Exception:
        pass

    # fallback: character-level for CJK
    try:
        if any("\u4e00" <= ch <= "\u9fff" for ch in text):
            return [ch for ch in text if ch.strip()]
    except Exception:
        pass

    return [t for t in text.lower().split() if t]


class BM25Service:
    """BM25 index manager with lazy rebuilding and batch operations."""

    def __init__(self, index_path: str | None = None) -> None:
        self.index_path = index_path or os.getenv(
            "BM25_INDEX_PATH", "data/indexes/bm25_index.pkl"
        )
        self.docs: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        self._bm25: BM25Okapi | None = None

        # Group cache
        self._group_caches: Dict[int, Dict[str, Any]] = {}
        self._cache_lock = threading.Lock()

        self._dirty: bool = False  # 標記索引是否需要重建
        self._dirty_groups: Set[int] = set()  # 記錄哪些 group 需要重建快取

        self._load()

    def _load(self) -> None:
        """Load index from disk."""
        try:
            if os.path.exists(self.index_path):
                try:
                    with open(self.index_path, "rb") as f:
                        data = pickle.load(f)
                        docs = data.get("docs", {}) if isinstance(data, dict) else {}
                        self.docs = docs
                        self._rebuild_index()
                        logger.debug(
                            "BM25 index loaded from %s (docs=%d)",
                            self.index_path,
                            len(self.docs),
                        )
                except (EOFError, pickle.UnpicklingError, ValueError) as e:
                    logger.warning(
                        "BM25 index at %s appears corrupted (%s). Rebuilding empty index.",
                        self.index_path,
                        type(e).__name__,
                    )
                    self.docs = {}
                    self._rebuild_index()
                    try:
                        self._persist()
                    except Exception:
                        logger.exception(
                            "Failed to persist rebuilt empty BM25 index to %s",
                            self.index_path,
                        )
            else:
                os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        except Exception:
            logger.exception("Failed to load BM25 index from %s", self.index_path)

    def _persist(self) -> None:
        """Persist index to disk atomically."""
        try:
            dirpath = os.path.dirname(self.index_path)
            if dirpath and not os.path.exists(dirpath):
                os.makedirs(dirpath, exist_ok=True)

            tmp_path = f"{self.index_path}.tmp"
            with open(tmp_path, "wb") as f:
                pickle.dump({"docs": self.docs}, f)

            try:
                os.replace(tmp_path, self.index_path)
            except Exception:
                try:
                    os.rename(tmp_path, self.index_path)
                except Exception:
                    logger.exception(
                        "Failed to move temp BM25 index %s -> %s",
                        tmp_path,
                        self.index_path,
                    )
        except Exception:
            logger.exception("Failed to persist BM25 index to %s", self.index_path)

    def _rebuild_index(self) -> None:
        """Rebuild global BM25 index from current docs."""
        try:
            tokenized = [_tokenize(c) for c, _ in self.docs.values()]
            if tokenized:
                self._bm25 = BM25Okapi(tokenized)
            else:
                self._bm25 = None

            with self._cache_lock:
                self._group_caches.clear()

            self._dirty = False
            self._dirty_groups.clear()

        except Exception:
            logger.exception("Failed to rebuild BM25 index")
            self._bm25 = None

    def batch_update(
        self,
        updates: List[Tuple[str, str, Dict[str, Any]]] = None,
        deletes: List[str] = None,
    ) -> None:
        """Batch update/delete documents without rebuilding index each time.

        Args:
            updates: List of (doc_id, content, payload) to add/update
            deletes: List of doc_ids to delete
        """
        modified_groups = set()

        # 批次刪除
        if deletes:
            for doc_id in deletes:
                if doc_id in self.docs:
                    _, payload = self.docs[doc_id]
                    try:
                        gid = int(payload.get("group_id", 0))
                        modified_groups.add(gid)
                    except Exception:
                        pass
                    del self.docs[doc_id]

        # 批次新增/更新
        if updates:
            for doc_id, content, payload in updates:
                self.docs[doc_id] = (content, payload)
                try:
                    gid = int(payload.get("group_id", 0))
                    modified_groups.add(gid)
                except Exception:
                    pass

        # 只重建一次索引
        if deletes or updates:
            self._rebuild_index()
            self._persist()
            logger.info(
                "BM25 batch update: %d deleted, %d updated/added, %d groups affected",
                len(deletes) if deletes else 0,
                len(updates) if updates else 0,
                len(modified_groups),
            )

    # =========================================

    def delete_chunk(self, doc_id: str, immediate: bool = False) -> None:
        """Delete a document from the BM25 index.

        Args:
            doc_id: Document ID to delete
            immediate: If True, rebuild index immediately. If False, mark as dirty.
        """
        try:
            if doc_id in self.docs:
                _, payload = self.docs[doc_id]
                try:
                    gid = int(payload.get("group_id", 0))
                    self._dirty_groups.add(gid)
                except Exception:
                    pass

                del self.docs[doc_id]
                self._dirty = True

                if immediate:
                    self._rebuild_index()
                    self._persist()
                    logger.debug("BM25: deleted doc %s (immediate)", doc_id)
                else:
                    logger.debug("BM25: marked doc %s for deletion (lazy)", doc_id)
            else:
                logger.debug("BM25: delete called for missing doc %s", doc_id)
        except Exception:
            logger.exception("BM25: error deleting doc %s", doc_id)

    def index_chunk(
        self,
        doc_id: str,
        content: str,
        payload: Dict[str, Any],
        immediate: bool = False,
    ) -> None:
        """Add or update a document in the BM25 index.

        Args:
            doc_id: Document ID
            content: Document content
            payload: Metadata
            immediate: If True, rebuild index immediately. If False, mark as dirty.
        """
        try:
            self.docs[doc_id] = (content, payload)
            self._dirty = True

            try:
                gid = int(payload.get("group_id", 0))
                self._dirty_groups.add(gid)
            except Exception:
                pass

            if immediate:
                self._rebuild_index()
                self._persist()
                logger.debug("BM25: indexed doc %s (immediate)", doc_id)
            else:
                logger.debug("BM25: marked doc %s for indexing (lazy)", doc_id)
        except Exception:
            logger.exception("BM25: failed to index doc %s", doc_id)

    def commit(self) -> None:
        """Force rebuild and persist if there are pending changes."""
        if self._dirty:
            logger.info("BM25: committing pending changes")
            self._rebuild_index()
            self._persist()

    def index_chunks_for_date_range(
        self, db: Session, group_id: int, start_dt: datetime, end_dt: datetime
    ) -> Dict[str, int]:
        """Index all ChunkMessageSummary rows for a group and date range (OPTIMIZED)."""
        repo = ChunkMessageSummaryRepository()
        chunks = repo.list_by_time_range(db, group_id, start_dt, end_dt)

        indexed = 0
        failed = 0

        updates = []
        deletes = []

        for ch in chunks:
            try:
                content = getattr(ch, "message_content", None)
                if not content:
                    continue

                doc_id = getattr(ch, "chunk_id", None) or str(getattr(ch, "id", ""))
                payload = {
                    "group_id": int(getattr(ch, "group_id", 0)),
                    "chunk_summary_id": int(getattr(ch, "id", 0)),
                }

                if doc_id in self.docs:
                    deletes.append(doc_id)

                updates.append((doc_id, content, payload))
                indexed += 1

            except Exception:
                logger.exception(
                    "BM25: unexpected error while processing chunk id %s",
                    getattr(ch, "id", "<unknown>"),
                )
                failed += 1

        try:
            self.batch_update(updates=updates, deletes=deletes)
        except Exception:
            logger.exception("BM25: batch update failed")
            failed += len(updates)
            indexed = 0

        stats = {"indexed": indexed, "failed": failed, "candidates": len(chunks)}
        logger.info(
            "BM25 indexing finished for group %d: indexed=%d failed=%d candidates=%d",
            group_id,
            indexed,
            failed,
            len(chunks),
        )
        return stats

    def _ensure_index_ready(self) -> None:
        """Rebuild index if marked as dirty."""
        if self._dirty:
            logger.debug("BM25: rebuilding index (was dirty)")
            self._rebuild_index()
            self._persist()

    def _get_or_build_group_cache(self, group_id: int) -> Dict[str, Any]:
        """Get or build cached BM25 index for a specific group."""
        self._ensure_index_ready()

        with self._cache_lock:
            if group_id in self._group_caches and group_id not in self._dirty_groups:
                logger.debug(f"BM25 cache hit for group {group_id}")
                return self._group_caches[group_id]

        import time

        start = time.time()

        ids = []
        contents = []
        for doc_id, (content, payload) in self.docs.items():
            try:
                if int(payload.get("group_id", 0)) == int(group_id):
                    ids.append(doc_id)
                    contents.append(content)
            except Exception:
                continue

        if not contents:
            cache = {"ids": [], "bm25": None, "tokenized": []}
        else:
            tokenized = [_tokenize(c) for c in contents]
            bm = BM25Okapi(tokenized)
            cache = {"ids": ids, "bm25": bm, "tokenized": tokenized}

        elapsed = time.time() - start
        logger.debug(
            f"BM25 cache built for group {group_id}: {len(ids)} docs in {elapsed:.2f}s"
        )

        with self._cache_lock:
            self._group_caches[group_id] = cache
            self._dirty_groups.discard(group_id)

        return cache

    def search(
        self, query: str, top_k: int = 30, group_id: int | None = None
    ) -> List[Tuple[str, float]]:
        """Search BM25 index with group filtering and caching."""
        try:
            self._ensure_index_ready()

            if not self.docs:
                return []

            if group_id is not None:
                cache = self._get_or_build_group_cache(group_id)
                ids = cache["ids"]
                bm = cache["bm25"]

                if not bm:
                    return []

                q_tokens = _tokenize(query)
                scores = bm.get_scores(q_tokens)
                pairs = list(zip(ids, scores))
                pairs.sort(key=lambda x: x[1], reverse=True)
                return pairs[:top_k]

            if not self._bm25:
                return []

            all_ids = list(self.docs.keys())
            q_tokens = _tokenize(query)
            scores = self._bm25.get_scores(q_tokens)
            pairs = list(zip(all_ids, scores))
            pairs.sort(key=lambda x: x[1], reverse=True)
            return pairs[:top_k]

        except Exception:
            logger.exception("BM25 search failed")
            return []


def index_chunks_for_date_range_background(
    group_id: int, start_date: str, end_date: str
) -> Dict[str, int]:
    """Background-friendly wrapper that creates its own DB session."""
    db = SessionLocal()
    try:
        sdt = _parse_datetime(start_date)
        edt = _parse_datetime(end_date)
        svc = get_bm25_service()
        return svc.index_chunks_for_date_range(db, group_id, sdt, edt)
    except Exception:
        logger.exception(
            "BM25 background task failed for group %s range %s - %s",
            group_id,
            start_date,
            end_date,
        )
        return {"indexed": 0, "failed": 0, "candidates": 0}
    finally:
        db.close()


__all__ = ["BM25Service", "get_bm25_service"]
