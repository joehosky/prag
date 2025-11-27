"""Check reindex progress by comparing database and Qdrant counts."""

import sys
import os
import io
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import SessionLocal
from app.models.chunk_message_summary import ChunkMessageSummary
from app.vector_store.qdrant_client import QdrantService

def main():
    print("=" * 60)
    print("REINDEX PROGRESS CHECK")
    print("=" * 60)

    # Count database records
    db = SessionLocal()
    try:
        total_db = db.query(ChunkMessageSummary).count()
        print(f"📊 Database chunks: {total_db}")
    finally:
        db.close()

    # Count Qdrant vectors
    qsvc = QdrantService()
    qdrant_count = qsvc.client.count(collection_name=qsvc.collection).count
    print(f"📊 Qdrant vectors: {qdrant_count}")

    # Calculate progress
    if total_db > 0:
        progress = (qdrant_count / total_db) * 100
        print(f"\n📈 Progress: {qdrant_count}/{total_db} ({progress:.1f}%)")

        if qdrant_count == total_db:
            print("✅ Status: COMPLETED")
        elif qdrant_count > 0:
            remaining = total_db - qdrant_count
            print(f"🔄 Status: IN PROGRESS ({remaining} remaining)")
        else:
            print("⚠️  Status: NOT STARTED")
    else:
        print("⚠️  No data in database")

    print("=" * 60)

if __name__ == "__main__":
    main()
