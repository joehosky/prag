from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.repositories.group_repo import GroupRepository
from app.models.line_group import LineGroup


class GroupService:
    def __init__(self, repo: Optional[GroupRepository] = None) -> None:
        self.repo = repo or GroupRepository()

    def create_group(
        self, db: Session, *, uniid: str, name: str, **kwargs
    ) -> LineGroup:
        payload: Dict[str, Any] = {"uniid": uniid, "name": name}
        payload.update(kwargs)
        obj = self.repo.create(db, payload)
        return obj

    def get_by_id(self, db: Session, id: int) -> Optional[LineGroup]:
        return self.repo.get(db, id)

    def get_by_uniid(self, db: Session, uniid: str) -> Optional[LineGroup]:
        return self.repo.get_by_uniid(db, uniid)

    def list_active(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> List[LineGroup]:
        return self.repo.list_active(db, skip=skip, limit=limit)

    def update_group(
        self, db: Session, db_obj: LineGroup, updates: Dict[str, Any]
    ) -> LineGroup:
        obj = self.repo.update(db, db_obj, updates)
        return obj

    def soft_delete(self, db: Session, db_obj: LineGroup) -> LineGroup:
        obj = self.repo.soft_delete(db, db_obj)
        return obj
