from typing import List, Optional, Dict, Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.line_group import LineGroup
from app.repositories.base import BaseRepository


class GroupRepository(BaseRepository[LineGroup]):
    def __init__(self) -> None:
        super().__init__(LineGroup)

    def get_by_uniid(self, db: Session, uniid: str) -> Optional[LineGroup]:
        stmt = select(LineGroup).where(
            LineGroup.uniid == uniid, LineGroup.deleted_at.is_(None)
        )
        return db.scalars(stmt).one_or_none()

    def list_active(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> List[LineGroup]:
        stmt = (
            select(LineGroup)
            .where(LineGroup.status == "active", LineGroup.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
        )
        return db.scalars(stmt).all()

    def soft_delete(self, db: Session, db_obj: LineGroup) -> LineGroup:
        from datetime import datetime, timezone

        db_obj.deleted_at = datetime.now(timezone.utc)
        return db_obj
