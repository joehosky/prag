from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.repositories.chunk_message_summary_repo import ChunkMessageSummaryRepository
from app.models.chunk_message_summary import ChunkMessageSummary


class ChunkMessageSummaryService:
    def __init__(self, repo: Optional[ChunkMessageSummaryRepository] = None) -> None:
        self.repo = repo or ChunkMessageSummaryRepository()

    def create_summary(
        self, db: Session, *, chunk_id: str, group_id: int, **kwargs
    ) -> ChunkMessageSummary:
        payload: Dict[str, Any] = {"chunk_id": chunk_id, "group_id": group_id}
        payload.update(kwargs)
        obj = self.repo.create(db, payload)
        return obj

    def get_by_id(self, db: Session, id: int) -> Optional[ChunkMessageSummary]:
        return self.repo.get(db, id)

    def get_by_chunk_id(
        self, db: Session, chunk_id: str
    ) -> Optional[ChunkMessageSummary]:
        return self.repo.get_by_chunk_id(db, chunk_id)

    def list_by_group(
        self, db: Session, group_id: int, skip: int = 0, limit: int = 100
    ) -> List[ChunkMessageSummary]:
        return self.repo.list_by_group(db, group_id, skip=skip, limit=limit)

    def list_by_time_range(
        self, db: Session, group_id: int, start_time, end_time
    ) -> List[ChunkMessageSummary]:
        return self.repo.list_by_time_range(db, group_id, start_time, end_time)

    def update_summary(
        self, db: Session, db_obj: ChunkMessageSummary, updates: Dict[str, Any]
    ) -> ChunkMessageSummary:
        return self.repo.update(db, db_obj, updates)

    def get_by_qdrant_point_id(
        self, db: Session, point_id: str
    ) -> Optional[ChunkMessageSummary]:
        return self.repo.get_by_qdrant_point_id(db, point_id)
