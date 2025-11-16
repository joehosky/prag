from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.line_group import LineGroup
from app.models.line_message import LineMessage
from app.services.group_service import GroupService
from app.services.message_service import MessageService


def setup_in_memory_db():
    engine = create_engine("sqlite:///:memory:", future=True)
    # Ensure related models are imported so SQLAlchemy can resolve relationships
    import app.models.line_message  # noqa: F401
    import app.models.line_group  # noqa: F401

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    return SessionLocal


def test_create_and_get_message():
    SessionLocal = setup_in_memory_db()
    with SessionLocal() as db:
        gsvc = GroupService()
        msvc = MessageService()

        group = gsvc.create_group(db, uniid="gm-1", name="G1")
        db.commit()
        db.refresh(group)

        msg = msvc.create_message(
            db, group_id=group.id, message_uid="m-1", message_content="hello"
        )
        db.commit()
        db.refresh(msg)

        assert msg.id is not None
        assert msg.group_id == group.id
        assert msg.message_uid == "m-1"

        fetched = msvc.get_by_id(db, msg.id)
        assert fetched is not None
        assert fetched.message_content == "hello"


def test_list_by_group_and_update():
    SessionLocal = setup_in_memory_db()
    with SessionLocal() as db:
        gsvc = GroupService()
        msvc = MessageService()

        group = gsvc.create_group(db, uniid="gm-2", name="G2")
        db.commit()
        db.refresh(group)

        m1 = msvc.create_message(
            db, group_id=group.id, message_uid="m-a", message_content="A"
        )
        m2 = msvc.create_message(
            db,
            group_id=group.id,
            message_uid="m-b",
            message_content="B",
            vector_processed=True,
        )
        db.commit()

        by_group = msvc.list_by_group(db, group.id)
        assert len(by_group) == 2

        unprocessed = msvc.list_unprocessed(db)
        assert any(x.message_uid == "m-a" for x in unprocessed)

        # update m1 to set vector_processed True and description
        msvc.update_message(
            db, m1, {"vector_processed": True, "message_description": "desc"}
        )
        db.commit()
        db.refresh(m1)

        assert m1.vector_processed is True
        assert m1.message_description == "desc"
