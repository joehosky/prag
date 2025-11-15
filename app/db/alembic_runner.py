"""Programmatic Alembic runner to apply existing migrations.

This runner is intended for development convenience: it applies
already-committed migrations (`alembic upgrade head`) at application
startup. It does NOT autogenerate migrations.
"""

from typing import Optional


def run_alembic_upgrade(
    alembic_ini_path: str = "alembic.ini", db_url: Optional[str] = None
) -> None:
    try:
        from alembic.config import Config
        from alembic import command
    except Exception as exc:  # alembic not installed
        raise RuntimeError("alembic is required to run migrations") from exc

    cfg = Config(alembic_ini_path)
    if db_url:
        cfg.set_main_option("sqlalchemy.url", db_url)

    # apply migrations to the head
    command.upgrade(cfg, "head")


__all__ = ["run_alembic_upgrade"]
