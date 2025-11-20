from __future__ import annotations

import os
import pickle
import logging
from typing import Dict, Tuple, List, Any
from datetime import datetime

from rank_bm25 import BM25Okapi

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.chunk_message_summary_repo import (
    ChunkMessageSummaryRepository,
)
from app.db.session import SessionLocal


def _parse_datetime(value: str) -> datetime:
    """Parse common datetime string formats into a timezone-naive datetime.

    Accepts ISO 8601-like strings. Falls back to trying '%Y-%m-%d' if time
    portion is not present.
    """
    if isinstance(value, datetime):
        return value
    try:
        # try ISO format first
        return datetime.fromisoformat(value)
    except Exception:
        pass
    # try date-only
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except Exception:
        raise


logger = logging.getLogger(__name__)


def _tokenize(text: str) -> List[str]:
    # simple whitespace tokenizer; keep lowercase for BM25
    return [t for t in text.lower().split() if t]


class BM25Service:
    """Simple BM25 index manager.

    This implementation keeps an in-memory mapping of doc_id -> (content, payload)
    and builds a rank_bm25 BM25Okapi index from the tokenized corpus. The index
    is persisted to disk as a pickled dict at `BM25_INDEX_PATH`.

    This is intentionally conservative and synchronous to match the project's
    POC requirements; for production you may want a separate process or service
    that manages indexing and concurrency.
    """

    def __init__(self, index_path: str | None = None) -> None:
        self.index_path = index_path or os.getenv(
            "BM25_INDEX_PATH", "data/indexes/bm25_index.pkl"
        )
        self.docs: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        self._bm25: BM25Okapi | None = None
        self._load()

    def _load(self) -> None:
        try:
            if os.path.exists(self.index_path):
                with open(self.index_path, "rb") as f:
                    data = pickle.load(f)
                    docs = data.get("docs", {}) if isinstance(data, dict) else {}
                    # ensure structure is doc_id -> (content, payload)
                    self.docs = docs
                    self._rebuild_index()
                    logger.debug(
                        "BM25 index loaded from %s (docs=%d)",
                        self.index_path,
                        len(self.docs),
                    )
            else:
                # ensure directory exists
                os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        except Exception:
            logger.exception("Failed to load BM25 index from %s", self.index_path)

    def _persist(self) -> None:
        try:
            with open(self.index_path, "wb") as f:
                pickle.dump({"docs": self.docs}, f)
        except Exception:
            logger.exception("Failed to persist BM25 index to %s", self.index_path)

    def _rebuild_index(self) -> None:
        # rebuild BM25 index from current docs
        try:
            tokenized = [_tokenize(c) for c, _ in self.docs.values()]
            if tokenized:
                self._bm25 = BM25Okapi(tokenized)
            else:
                self._bm25 = None
        except Exception:
            logger.exception("Failed to rebuild BM25 index")
            self._bm25 = None

    def delete_chunk(self, doc_id: str) -> None:
        """Delete a document from the BM25 index (best-effort).

        If the document is not present, this is a no-op.
        """
        try:
            if doc_id in self.docs:
                del self.docs[doc_id]
                self._rebuild_index()
                self._persist()
                logger.debug("BM25: deleted doc %s", doc_id)
            else:
                logger.debug("BM25: delete called for missing doc %s", doc_id)
        except Exception:
            logger.exception("BM25: error deleting doc %s", doc_id)

    def index_chunk(self, doc_id: str, content: str, payload: Dict[str, Any]) -> None:
        """Add or update a document in the BM25 index and persist the index."""
        try:
            self.docs[doc_id] = (content, payload)
            self._rebuild_index()
            self._persist()
            logger.debug("BM25: indexed doc %s", doc_id)
        except Exception:
            logger.exception("BM25: failed to index doc %s", doc_id)

    def index_chunks_for_date_range(
        self, db: Session, group_id: int, start_dt: datetime, end_dt: datetime
    ) -> Dict[str, int]:
        """Index all ChunkMessageSummary rows for a group and date range.

        Returns a dict with statistics: {'indexed': int, 'failed': int, 'candidates': int}
        """
        repo = ChunkMessageSummaryRepository()
        chunks = repo.list_by_time_range(db, group_id, start_dt, end_dt)
        indexed = 0
        failed = 0
        for ch in chunks:
            try:
                # read content using snake_case model fields
                content = getattr(ch, "message_content", None)
                if not content:
                    continue

                doc_id = getattr(ch, "chunk_id", None) or str(getattr(ch, "id", ""))
                payload = {
                    "group_id": int(getattr(ch, "group_id", 0)),
                    "chunk_summary_id": int(getattr(ch, "id", 0)),
                }

                # delete existing doc (best-effort)
                try:
                    self.delete_chunk(doc_id)
                except Exception:
                    logger.exception("BM25: delete existing doc error for %s", doc_id)

                # index
                try:
                    self.index_chunk(doc_id, content, payload)
                    indexed += 1
                except Exception:
                    logger.exception("BM25: index error for doc %s", doc_id)
                    failed += 1
            except Exception:
                logger.exception(
                    "BM25: unexpected error while processing chunk id %s",
                    getattr(ch, "id", "<unknown>"),
                )
                failed += 1
        stats = {"indexed": indexed, "failed": failed, "candidates": len(chunks)}
        logger.debug(
            "BM25 indexing finished for group %s indexed:%d failed:%d candidates:%d",
            group_id,
            indexed,
            failed,
            len(chunks),
        )
        return stats


def index_chunks_for_date_range_background(
    group_id: int, start_date: str, end_date: str
) -> Dict[str, int]:
    """Background-friendly wrapper that creates its own DB session.

    `start_date` and `end_date` are expected to be ISO or RFC3339 strings; this
    function will parse them using `app.utils.datetime_utils.parse_datetime`.
    Designed to be called via FastAPI `BackgroundTasks.add_task`.
    """
    db = SessionLocal()
    try:
        sdt = _parse_datetime(start_date)
        edt = _parse_datetime(end_date)
        svc = BM25Service()
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


__all__ = ["BM25Service"]
