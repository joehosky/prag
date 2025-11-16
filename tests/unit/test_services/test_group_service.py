import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.line_group import LineGroup
from app.services.group_service import GroupService


def setup_in_memory_db():
    engine = create_engine("sqlite:///:memory:", future=True)
    import app.models.line_message  # Ensure related models are imported so SQLAlchemy can resolve relationships

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    return SessionLocal


def test_create_and_get_group():
    SessionLocal = setup_in_memory_db()
    with SessionLocal() as db:
        service = GroupService()

        group = service.create_group(db, uniid="g-123", name="Test Group")
        db.commit()
        db.refresh(group)

        assert group.id is not None
        assert group.uniid == "g-123"
        assert group.name == "Test Group"

        fetched = service.get_by_uniid(db, "g-123")
        assert fetched is not None
        assert fetched.id == group.id


def test_list_active_and_soft_delete():
    SessionLocal = setup_in_memory_db()
    with SessionLocal() as db:
        service = GroupService()

        g1 = service.create_group(db, uniid="g-a", name="A")
        g2 = service.create_group(db, uniid="g-b", name="B", status="inactive")
        db.commit()

        active = service.list_active(db)
        assert any(x.uniid == "g-a" for x in active)
        assert all(x.status == "active" for x in active)

        # soft delete g1
        service.soft_delete(db, g1)
        db.commit()

        post = service.get_by_uniid(db, "g-a")
        assert post is None
