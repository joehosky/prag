from __future__ import annotations

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config

if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        pass

# If alembic.ini uses a placeholder URL (e.g. 'driver:///'), try to
# fall back to the application's settings.database_url for local/dev use.
try:
    url_opt = config.get_main_option("sqlalchemy.url")
    if not url_opt or url_opt.startswith("driver"):
        try:
            from app.core.config import settings

            config.set_main_option("sqlalchemy.url", settings.database_url)
        except Exception:
            # If settings cannot be imported, leave the config as-is and
            # let engine_from_config raise a clear error later.
            pass
except Exception:
    pass

try:
    from app.db.base import Base
    import importlib

    try:
        importlib.import_module("app.models.line_group")
        importlib.import_module("app.models.line_message")
    except Exception:
        pass

    target_metadata = Base.metadata
except Exception:
    target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode."""
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
