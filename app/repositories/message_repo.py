from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.line_message import LineMessage
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository[LineMessage]):
    def __init__(self) -> None:
        super().__init__(LineMessage)

    def get_by_message_uid(
        self, db: Session, message_uid: str
    ) -> Optional[LineMessage]:
        stmt = select(LineMessage).where(LineMessage.message_uid == message_uid)
        return db.scalars(stmt).one_or_none()

    def list_by_group(
        self, db: Session, group_id: int, skip: int = 0, limit: int = 100
    ) -> List[LineMessage]:
        stmt = (
            select(LineMessage)
            .where(LineMessage.group_id == group_id)
            .offset(skip)
            .limit(limit)
        )
        return db.scalars(stmt).all()

    def list_unprocessed(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> List[LineMessage]:
        stmt = (
            select(LineMessage)
            .where(LineMessage.vector_processed.is_(False))
            .offset(skip)
            .limit(limit)
        )
        return db.scalars(stmt).all()

    def list_by_chunk_id(self, db: Session, chunk_id: str) -> List[LineMessage]:
        stmt = select(LineMessage).where(LineMessage.chunk_id == chunk_id)
        return db.scalars(stmt).all()

    def list_by_time_range(
        self, db: Session, group_id: int, start_time, end_time
    ) -> List[LineMessage]:
        stmt = (
            select(LineMessage)
            .where(
                LineMessage.group_id == group_id,
                LineMessage.message_time >= start_time,
                LineMessage.message_time <= end_time,
            )
            .order_by(LineMessage.message_time.asc())
        )
        return db.scalars(stmt).all()
