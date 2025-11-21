"""DB lookup tool to find chunk_ids for a group in a time range."""

from __future__ import annotations

from typing import List, Optional
from app.db.session import SessionLocal
from app.repositories.group_repo import GroupRepository
from app.repositories.chunk_message_summary_repo import ChunkMessageSummaryRepository


def db_lookup_chunks(
    group_uniid: str, start_time: Optional[str], end_time: Optional[str]
) -> List[str]:
    """Return list of chunk_id strings that match the group and time range.

    If start_time or end_time is missing, returns empty list (no prefilter).
    """
    if not start_time or not end_time:
        return []

    db = SessionLocal()
    try:
        grp = GroupRepository().get_by_uniid(db, group_uniid)
        if not grp:
            return []
        gid = int(getattr(grp, "id", 0))

        repo = ChunkMessageSummaryRepository()
        rows = repo.list_by_time_range(db, gid, start_time, end_time)
        return [getattr(r, "chunk_id") for r in rows if getattr(r, "chunk_id", None)]
    finally:
        try:
            db.close()
        except Exception:
            pass
