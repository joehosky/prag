from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.repositories.group_message_summary_repo import (
    GroupMessageSummaryRepository,
)
from app.models.group_message_summary import GroupMessageSummary


class GroupMessageSummaryService:
    def __init__(self, repo: Optional[GroupMessageSummaryRepository] = None) -> None:
        self.repo = repo or GroupMessageSummaryRepository()

    def create_summary(
        self,
        db: Session,
        *,
        group_id: int,
        message_time=None,
        message_description: Optional[str] = None,
    ) -> GroupMessageSummary:
        payload: Dict[str, Any] = {
            "group_id": group_id,
            "message_time": message_time,
            "message_description": message_description,
        }
        obj = self.repo.create(db, payload)
        return obj

    def get_by_id(self, db: Session, id: int) -> Optional[GroupMessageSummary]:
        return self.repo.get_by_id(db, id)

    def list_by_group(self, db: Session, group_id: int) -> List[GroupMessageSummary]:
        return self.repo.list_by_group(db, group_id)

    def list_by_time_range(self, db: Session, group_id: int, start_time, end_time):
        return self.repo.list_by_time_range(db, group_id, start_time, end_time)

    def update_summary(
        self, db: Session, db_obj: GroupMessageSummary, updates: Dict[str, Any]
    ) -> GroupMessageSummary:
        return self.repo.update(db, db_obj, updates)

    def get_latest_for_group(
        self, db: Session, group_id: int
    ) -> Optional[GroupMessageSummary]:
        return self.repo.get_latest_for_group(db, group_id)
