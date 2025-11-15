"""Drop all tables in the configured database.

Usage:
  python scripts/drop_all_tables.py --yes

This script reflects the database metadata and drops all tables. It requires
the explicit `--yes` flag to perform the destructive action to avoid
accidental data loss.
"""

from __future__ import annotations

import sys
from typing import Iterable

from sqlalchemy import MetaData, text

from app.db.session import engine
from app.core.config import settings


def list_tables() -> Iterable[str]:
    meta = MetaData()
    meta.reflect(bind=engine)
    return list(meta.tables.keys())


def drop_all() -> None:
    meta = MetaData()
    meta.reflect(bind=engine)
    if not meta.tables:
        print("No tables found.")
        return
    print(f"Dropping {len(meta.tables)} table(s): {', '.join(meta.tables.keys())}")
    meta.drop_all(bind=engine)
    # Ensure any lingering sequences or objects are cleaned if DB supports it
    try:
        with engine.connect() as conn:
            conn.execute(text("VACUUM;"))
    except Exception:
        pass


def main() -> int:
    db_url = settings.database_url
    print(f"Target DB: {db_url}")

    if "--yes" not in sys.argv:
        print("This is a destructive operation. Re-run with --yes to confirm.")
        tables = list_tables()
        print(f"Found tables: {', '.join(tables) if tables else 'none'}")
        return 2

    drop_all()
    print("Drop complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
