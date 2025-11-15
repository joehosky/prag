from typing import Optional

from sqlalchemy import Engine

from app.db import session as db_session
from app.db.base import Base


def init_db(engine: Optional[Engine] = None) -> None:
    """Create all tables for development.

    If `engine` is not provided, the function uses the engine from
    `app.db.session.engine`.
    """
    engine_to_use = engine or db_session.engine
    Base.metadata.create_all(bind=engine_to_use)


__all__ = ["init_db"]
