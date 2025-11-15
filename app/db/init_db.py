from typing import Optional

from sqlalchemy import Engine

from app.db import session as db_session
from app.db.base import Base


def init_db(engine: Optional[Engine] = None) -> None:
    """Create all tables for development.

    This is a simple convenience helper for local development and tests.
    Prefer using Alembic migrations for schema changes in team or
    production environments.
    """
    engine_to_use = engine or db_session.engine
    Base.metadata.create_all(bind=engine_to_use)


__all__ = ["init_db"]
