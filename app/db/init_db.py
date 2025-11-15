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

    # Ensure model modules are imported so that Declarative Base metadata is
    # populated before calling create_all(). Importing here avoids forcing
    # package-level imports that previously caused circular import issues.
    try:
        # import models explicitly
        from importlib import import_module

        import_module("app.models.line_group")
        import_module("app.models.line_message")
    except Exception:
        # if imports fail, proceed — create_all will simply act on whatever
        # metadata is available
        pass

    Base.metadata.create_all(bind=engine_to_use)


__all__ = ["init_db"]
