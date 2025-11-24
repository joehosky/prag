#!/usr/bin/env python3
"""Schedule BM25 reindexing for days already marked as chunk_summary.

Usage:
  python scripts/schedule_bm25_from_tags.py [--group-uniid UNI] [--dry-run]

This script iterates MessageSummaryTag entries and for each tag with
`chunk_summary==True` it calls `index_chunks_for_date_range_background(group_id, start_date_iso, end_date_iso)`
so BM25 indexing runs without re-running the LLM summarization.
"""
from datetime import datetime, time as dt_time
import argparse
import logging
import os
import sys

# Ensure project root is on sys.path when running script directly
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.db.session import SessionLocal
from app.repositories.message_summary_tag_repo import MessageSummaryTagRepository
from app.repositories.group_repo import GroupRepository
from app.services.bm25_service import index_chunks_for_date_range_background

logger = logging.getLogger("scripts.schedule_bm25_from_tags")
logging.basicConfig(level=logging.INFO)


def main(group_uniid: str | None = None, dry_run: bool = False) -> None:
    db = SessionLocal()
    try:
        grp_repo = GroupRepository()
        tag_repo = MessageSummaryTagRepository()

        groups = []
        if group_uniid:
            g = grp_repo.get_by_uniid(db, group_uniid)
            if not g:
                logger.error("Group with uniid %s not found", group_uniid)
                return
            groups = [g]
        else:
            # load active groups; if many groups exist consider paging here
            groups = grp_repo.list_active(db, skip=0, limit=1000)

        logger.info("Found %d groups to inspect", len(groups))

        tag_repo = MessageSummaryTagRepository()

        # If group_uniid provided, limit to that group's tags; otherwise iterate all tags
        if group_uniid:
            grp_repo = GroupRepository()
            g = grp_repo.get_by_uniid(db, group_uniid)
            if not g:
                logger.error("Group with uniid %s not found", group_uniid)
                return
            tags = tag_repo.list_by_group(db, g.id)
        else:
            tags = tag_repo.list_all(db)

        logger.info("Found %d tags to inspect", len(tags))

        for t in tags:
            try:
                if not getattr(t, "chunk_summary", False):
                    continue
                gid = getattr(t, "group_id", None)
                st = getattr(t, "summary_time", None)
                if gid is None:
                    logger.warning(
                        "Skipping tag id=%s with no group_id", getattr(t, "id", None)
                    )
                    continue
                if not st:
                    logger.warning(
                        "Tag id=%s for group %s has chunk_summary=True but no summary_time, skipping",
                        getattr(t, "id", None),
                        gid,
                    )
                    continue

                # build start/end ISO strings for the day
                day = st.date()
                day_start = datetime.combine(day, dt_time.min)
                day_end = datetime.combine(day, dt_time(23, 59, 59, 999000))
                s_iso = day_start.isoformat()
                e_iso = day_end.isoformat()

                logger.info(
                    "Scheduling BM25 for group=%s day=%s tag_id=%s dry_run=%s",
                    gid,
                    day,
                    getattr(t, "id", None),
                    dry_run,
                )

                if not dry_run:
                    try:
                        # This function creates its own DB session and runs indexing
                        index_chunks_for_date_range_background(gid, s_iso, e_iso)
                    except Exception:
                        logger.exception(
                            "Failed to schedule/index BM25 for group %s day %s",
                            gid,
                            day,
                        )
            except Exception:
                logger.exception(
                    "Unexpected error while processing tag id=%s",
                    getattr(t, "id", None),
                )

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--group-uniid", dest="group_uniid", help="Optional group uniid to limit to"
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Don't actually call indexing, just print",
    )
    ns = parser.parse_args()
    main(group_uniid=ns.group_uniid, dry_run=ns.dry_run)
