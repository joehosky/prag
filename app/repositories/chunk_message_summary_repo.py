from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chunk_message_summary import ChunkMessageSummary
from app.repositories.base import BaseRepository


class ChunkMessageSummaryRepository(BaseRepository[ChunkMessageSummary]):
    def __init__(self) -> None:
        super().__init__(ChunkMessageSummary)

    def get_by_chunk_id(
        self, db: Session, chunk_id: str
    ) -> Optional[ChunkMessageSummary]:
        stmt = select(ChunkMessageSummary).where(
            ChunkMessageSummary.chunk_id == chunk_id
        )
        return db.scalars(stmt).one_or_none()

    def list_by_group(
        self, db: Session, group_id: int, skip: int = 0, limit: int = 100
    ) -> List[ChunkMessageSummary]:
        stmt = (
            select(ChunkMessageSummary)
            .where(ChunkMessageSummary.group_id == group_id)
            .offset(skip)
            .limit(limit)
        )
        return db.scalars(stmt).all()

    def list_by_time_range(
        self, db: Session, group_id: int, start_time, end_time
    ) -> List[ChunkMessageSummary]:
        stmt = select(ChunkMessageSummary).where(
            ChunkMessageSummary.group_id == group_id,
            ChunkMessageSummary.start_time >= start_time,
            ChunkMessageSummary.end_time <= end_time,
        )
        return db.scalars(stmt).all()

    def get_by_qdrant_point_id(
        self, db: Session, point_id: str
    ) -> Optional[ChunkMessageSummary]:
        stmt = select(ChunkMessageSummary).where(
            ChunkMessageSummary.qdrant_point_id == point_id
        )
        return db.scalars(stmt).one_or_none()

    def find_by_group_and_day(
        self, db: Session, group_id: int, day_start, day_end
    ) -> List[ChunkMessageSummary]:
        """Find all summaries for a group that exactly match the day's start/end."""
        stmt = select(ChunkMessageSummary).where(
            ChunkMessageSummary.group_id == group_id,
            ChunkMessageSummary.start_time == day_start,
            ChunkMessageSummary.end_time == day_end,
        )
        return db.scalars(stmt).all()

    def delete_by_group_and_day(
        self, db: Session, group_id: int, day_start, day_end
    ) -> List[ChunkMessageSummary]:
        """Delete summaries for a group/day and return the deleted objects."""
        old = self.find_by_group_and_day(db, group_id, day_start, day_end)
        for obj in old:
            db.delete(obj)
        return old

    def create_summary(self, db: Session, summary_in: dict) -> ChunkMessageSummary:
        """Convenience wrapper around BaseRepository.create for summaries."""
        return self.create(db, summary_in)
