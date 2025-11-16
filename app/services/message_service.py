from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.repositories.message_repo import MessageRepository
from app.models.line_message import LineMessage


class MessageService:
    def __init__(self, repo: Optional[MessageRepository] = None) -> None:
        self.repo = repo or MessageRepository()

    def create_message(self, db: Session, *, group_id: int, **kwargs) -> LineMessage:
        payload: Dict[str, Any] = {"group_id": group_id}
        payload.update(kwargs)
        obj = self.repo.create(db, payload)
        return obj

    def get_by_id(self, db: Session, id: int) -> Optional[LineMessage]:
        return self.repo.get(db, id)

    def get_by_message_uid(
        self, db: Session, message_uid: str
    ) -> Optional[LineMessage]:
        return self.repo.get_by_message_uid(db, message_uid)

    def list_by_group(
        self, db: Session, group_id: int, skip: int = 0, limit: int = 100
    ) -> List[LineMessage]:
        return self.repo.list_by_group(db, group_id, skip=skip, limit=limit)

    def list_unprocessed(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> List[LineMessage]:
        return self.repo.list_unprocessed(db, skip=skip, limit=limit)

    def update_message(
        self, db: Session, db_obj: LineMessage, updates: Dict[str, Any]
    ) -> LineMessage:
        return self.repo.update(db, db_obj, updates)

    def list_by_chunk_id(self, db: Session, chunk_id: str) -> List[LineMessage]:
        return self.repo.list_by_chunk_id(db, chunk_id)
