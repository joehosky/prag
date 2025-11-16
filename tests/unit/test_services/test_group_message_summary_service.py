from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.line_group import LineGroup
from app.models.group_message_summary import GroupMessageSummary
from app.services.group_service import GroupService
from app.services.group_message_summary_service import GroupMessageSummaryService


def setup_in_memory_db():
    engine = create_engine("sqlite:///:memory:", future=True)
    # Ensure related models are imported so SQLAlchemy can resolve relationships
    import app.models.line_message  # noqa: F401
    import app.models.chunk_message_summary  # noqa: F401
    import app.models.group_message_summary  # noqa: F401

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    return SessionLocal


def test_create_and_get_group_summary():
    SessionLocal = setup_in_memory_db()
    with SessionLocal() as db:
        gsvc = GroupService()
        ssvc = GroupMessageSummaryService()

        grp = gsvc.create_group(db, uniid="g-s-1", name="G1")
        db.commit()
        db.refresh(grp)

        now = datetime.now(timezone.utc)
        summary = ssvc.create_summary(
            db, group_id=grp.id, message_time=now, message_description="desc"
        )
        db.commit()
        db.refresh(summary)

        assert summary.id is not None
        assert summary.group_id == grp.id
        fetched = ssvc.get_by_id(db, summary.id)
        assert fetched is not None
        assert fetched.message_description == "desc"


def test_list_by_group_and_time_range():
    SessionLocal = setup_in_memory_db()
    with SessionLocal() as db:
        gsvc = GroupService()
        ssvc = GroupMessageSummaryService()

        grp = gsvc.create_group(db, uniid="g-s-2", name="G2")
        db.commit()
        db.refresh(grp)

        base = datetime.now(timezone.utc)
        s1 = ssvc.create_summary(db, group_id=grp.id, message_time=base)
        s2 = ssvc.create_summary(
            db, group_id=grp.id, message_time=base + timedelta(minutes=1)
        )
        db.commit()

        all_for_group = ssvc.list_by_group(db, grp.id)
        assert len(all_for_group) == 2

        results = ssvc.list_by_time_range(db, grp.id, base, base + timedelta(minutes=2))
        assert len(results) >= 2

        ssvc.update_summary(db, s1, {"message_description": "updated"})
        db.commit()
        db.refresh(s1)
        assert s1.message_description == "updated"
