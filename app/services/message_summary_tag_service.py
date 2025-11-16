from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.repositories.message_summary_tag_repo import MessageSummaryTagRepository
from app.models.message_summary_tag import MessageSummaryTag


class MessageSummaryTagService:
    def __init__(self, repo: Optional[MessageSummaryTagRepository] = None) -> None:
        self.repo = repo or MessageSummaryTagRepository()

    def create_tag(
        self,
        db: Session,
        *,
        group_id: int,
        summary_time=None,
        chunk_summary: bool = False,
        daily_summary: bool = False,
        chunk_current_retry: int = 0,
        daily_current_retry: int = 0,
    ) -> MessageSummaryTag:
        payload: Dict[str, Any] = {
            "group_id": group_id,
            "summary_time": summary_time,
            "chunk_summary": chunk_summary,
            "daily_summary": daily_summary,
            "chunk_current_retry": chunk_current_retry,
            "daily_current_retry": daily_current_retry,
        }
        obj = self.repo.create(db, payload)
        return obj

    def get_by_id(self, db: Session, id: int) -> Optional[MessageSummaryTag]:
        return self.repo.get_by_id(db, id)

    def list_by_group(self, db: Session, group_id: int) -> List[MessageSummaryTag]:
        return self.repo.list_by_group(db, group_id)

    def list_pending_chunk(self, db: Session, group_id: int) -> List[MessageSummaryTag]:
        return self.repo.list_pending_chunk(db, group_id)

    def list_pending_daily(self, db: Session, group_id: int) -> List[MessageSummaryTag]:
        return self.repo.list_pending_daily(db, group_id)

    def update_tag(
        self, db: Session, db_obj: MessageSummaryTag, updates: Dict[str, Any]
    ) -> MessageSummaryTag:
        return self.repo.update(db, db_obj, updates)
