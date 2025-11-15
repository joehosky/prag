from __future__ import annotations

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

import os

# this is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# If the application exposes a settings object with the DB URL, prefer that
# for CLI runs so developers don't need to edit alembic.ini locally.
try:
    from app.core.config import settings

    if getattr(settings, "database_url", None):
        config.set_main_option("sqlalchemy.url", settings.database_url)
except Exception:
    # ignore — fall back to alembic.ini
    pass

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        pass

# Import your project's MetaData object here
try:
    # Use the same Declarative Base used by the application models
    # (app.db.base.Base) so that metadata contains the model tables.
    from app.db.base import Base

    # Import model modules so that Base.metadata is populated for autogenerate.
    try:
        import importlib

        importlib.import_module("app.models.line_group")
        importlib.import_module("app.models.line_message")
    except Exception:
        pass

    target_metadata = Base.metadata
except Exception:
    target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation we
    don't even need a DBAPI to be available.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
