from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.line_group import LineGroup
from app.models.message_summary_tag import MessageSummaryTag
from app.services.group_service import GroupService
from app.services.message_summary_tag_service import MessageSummaryTagService


def setup_in_memory_db():
    engine = create_engine("sqlite:///:memory:", future=True)
    # Ensure related models are imported so SQLAlchemy can resolve relationships
    import app.models.line_message  # noqa: F401
    import app.models.chunk_message_summary  # noqa: F401
    import app.models.group_message_summary  # noqa: F401
    import app.models.message_summary_tag  # noqa: F401

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    return SessionLocal


def test_create_and_get_tag():
    SessionLocal = setup_in_memory_db()
    with SessionLocal() as db:
        gsvc = GroupService()
        tsvc = MessageSummaryTagService()

        grp = gsvc.create_group(db, uniid="tag-1", name="T1")
        db.commit()
        db.refresh(grp)

        now = datetime.now(timezone.utc)
        tag = tsvc.create_tag(db, group_id=grp.id, summary_time=now)
        db.commit()
        db.refresh(tag)

        assert tag.id is not None
        assert tag.group_id == grp.id
        fetched = tsvc.get_by_id(db, tag.id)
        assert fetched is not None


def test_list_by_group_and_update():
    SessionLocal = setup_in_memory_db()
    with SessionLocal() as db:
        gsvc = GroupService()
        tsvc = MessageSummaryTagService()

        grp = gsvc.create_group(db, uniid="tag-2", name="T2")
        db.commit()
        db.refresh(grp)

        t1 = tsvc.create_tag(db, group_id=grp.id)
        t2 = tsvc.create_tag(db, group_id=grp.id)
        db.commit()

        all_tags = tsvc.list_by_group(db, grp.id)
        assert len(all_tags) == 2

        # update a tag
        tsvc.update_tag(db, t1, {"chunk_summary": True})
        db.commit()
        db.refresh(t1)
        assert t1.chunk_summary is True
