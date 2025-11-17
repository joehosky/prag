from typing import Generic, Type, TypeVar, List, Optional, Dict, Any

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic repository with common helpers.

    Implements basic CRUD helpers using SQLAlchemy 2.0 style (`select` + `Session.scalars`).
    """

    def __init__(self, model: Type[T]):
        self.model = model

    def get(self, db: Session, id: int) -> Optional[T]:
        return db.get(self.model, id)

    def list(self, db: Session, skip: int = 0, limit: int = 100) -> List[T]:
        stmt = select(self.model).offset(skip).limit(limit)
        return db.scalars(stmt).all()

    def create(self, db: Session, obj_in: Dict[str, Any]) -> T:
        # Ensure timestamps are present to satisfy NOT NULL DB constraints when
        # the DB column has no server-default. Use UTC timestamps.
        now = datetime.now(timezone.utc)
        if "created_at" not in obj_in:
            obj_in["created_at"] = now
        if "updated_at" not in obj_in:
            obj_in["updated_at"] = now

        obj = self.model(**obj_in)
        db.add(obj)
        return obj

    def update(self, db: Session, db_obj: T, obj_in: Dict[str, Any]) -> T:
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        return db_obj

    def delete(self, db: Session, db_obj: T) -> None:
        db.delete(db_obj)
