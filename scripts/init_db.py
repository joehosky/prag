"""
Initialize PostgreSQL Database
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from app.db.base import Base
from app.core.config import settings


def init_database():
    """Initialize database tables"""
    print("Initializing database...")
    print(f"Database URL: {settings.database_url}")

    try:
        engine = create_engine(settings.database_url)
        Base.metadata.create_all(bind=engine)
        print("✓ Database initialized successfully!")
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        print("Please make sure PostgreSQL is running and credentials are correct.")
        return False

    return True


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
