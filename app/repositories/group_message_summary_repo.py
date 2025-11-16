from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.models.group_message_summary import GroupMessageSummary
from app.repositories.base import BaseRepository


class GroupMessageSummaryRepository(BaseRepository[GroupMessageSummary]):
    def __init__(self) -> None:
        super().__init__(GroupMessageSummary)

    def get_by_id(self, db: Session, id: int) -> Optional[GroupMessageSummary]:
        return self.get(db, id)

    def list_by_group(self, db: Session, group_id: int) -> List[GroupMessageSummary]:
        stmt = select(GroupMessageSummary).where(
            GroupMessageSummary.group_id == group_id
        )
        return db.scalars(stmt).all()

    def list_by_time_range(
        self, db: Session, group_id: int, start_time, end_time
    ) -> List[GroupMessageSummary]:
        stmt = select(GroupMessageSummary).where(
            and_(
                GroupMessageSummary.group_id == group_id,
                GroupMessageSummary.message_time >= start_time,
                GroupMessageSummary.message_time <= end_time,
            )
        )
        return db.scalars(stmt).all()

    def get_latest_for_group(
        self, db: Session, group_id: int
    ) -> Optional[GroupMessageSummary]:
        stmt = (
            select(GroupMessageSummary)
            .where(GroupMessageSummary.group_id == group_id)
            .order_by(GroupMessageSummary.message_time.desc())
            .limit(1)
        )
        return db.scalars(stmt).one_or_none()
