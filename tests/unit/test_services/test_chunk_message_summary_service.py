from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.line_group import LineGroup
from app.models.chunk_message_summary import ChunkMessageSummary
from app.services.group_service import GroupService
from app.services.chunk_message_summary_service import ChunkMessageSummaryService


def setup_in_memory_db():
    engine = create_engine("sqlite:///:memory:", future=True)
    # Ensure related models are imported
    import app.models.line_group  # noqa: F401
    import app.models.line_message  # noqa: F401
    import app.models.chunk_message_summary  # noqa: F401

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    return SessionLocal


def test_create_and_get_summary():
    SessionLocal = setup_in_memory_db()
    with SessionLocal() as db:
        gsvc = GroupService()
        ssvc = ChunkMessageSummaryService()

        grp = gsvc.create_group(db, uniid="cg-1", name="G1")
        db.commit()
        db.refresh(grp)

        start = datetime.now(timezone.utc)
        end = start + timedelta(minutes=5)

        summary = ssvc.create_summary(
            db,
            chunk_id="chunk-1",
            group_id=grp.id,
            start_time=start,
            end_time=end,
            message_ids="1,2,3",
            message_content="raw",
            message_summary="summary",
        )
        db.commit()
        db.refresh(summary)

        assert summary.id is not None
        assert summary.chunk_id == "chunk-1"
        fetched = ssvc.get_by_chunk_id(db, "chunk-1")
        assert fetched is not None
        assert fetched.message_summary == "summary"


def test_list_by_group_and_time_range():
    SessionLocal = setup_in_memory_db()
    with SessionLocal() as db:
        gsvc = GroupService()
        ssvc = ChunkMessageSummaryService()

        grp = gsvc.create_group(db, uniid="cg-2", name="G2")
        db.commit()
        db.refresh(grp)

        base = datetime.now(timezone.utc)
        s1 = ssvc.create_summary(
            db, chunk_id="c1", group_id=grp.id, start_time=base, end_time=base
        )
        s2 = ssvc.create_summary(
            db, chunk_id="c2", group_id=grp.id, start_time=base, end_time=base
        )
        db.commit()

        all_for_group = ssvc.list_by_group(db, grp.id)
        assert len(all_for_group) == 2

        # time range that includes both
        results = ssvc.list_by_time_range(db, grp.id, base, base)
        assert len(results) >= 2

        # update summary text
        ssvc.update_summary(db, s1, {"message_summary": "new"})
        db.commit()
        db.refresh(s1)
        assert s1.message_summary == "new"
