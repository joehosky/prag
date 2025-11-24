from typing import List, Optional, Dict, Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.message_summary_tag import MessageSummaryTag
from app.repositories.base import BaseRepository


class MessageSummaryTagRepository(BaseRepository[MessageSummaryTag]):
    def __init__(self) -> None:
        super().__init__(MessageSummaryTag)

    def get_by_id(self, db: Session, id: int) -> Optional[MessageSummaryTag]:
        return self.get(db, id)

    def list_by_group(self, db: Session, group_id: int) -> List[MessageSummaryTag]:
        stmt = select(MessageSummaryTag).where(MessageSummaryTag.group_id == group_id)
        return db.scalars(stmt).all()

    def list_pending_chunk(self, db: Session, group_id: int) -> List[MessageSummaryTag]:
        stmt = select(MessageSummaryTag).where(
            MessageSummaryTag.group_id == group_id,
            MessageSummaryTag.chunk_summary.is_(False),
        )
        return db.scalars(stmt).all()

    def list_pending_daily(self, db: Session, group_id: int) -> List[MessageSummaryTag]:
        stmt = select(MessageSummaryTag).where(
            MessageSummaryTag.group_id == group_id,
            MessageSummaryTag.daily_summary.is_(False),
        )
        return db.scalars(stmt).all()

    def list_all(self, db: Session) -> List[MessageSummaryTag]:
        """Return all MessageSummaryTag rows."""
        stmt = select(MessageSummaryTag)
        return db.scalars(stmt).all()
