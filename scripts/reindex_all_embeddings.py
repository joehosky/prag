"""Re-index all message embeddings using local embedding model.

This script:
1. Fetches all chunk_message_summaries from database
2. Re-generates embeddings using the configured local model (768-dim)
3. Updates Qdrant vector store with new embeddings
4. Updates database with new qdrant_point_id and embedding

Usage:
    python scripts/reindex_all_embeddings.py [--batch-size 100] [--dry-run]
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.chunk_message_summary import ChunkMessageSummary
from app.repositories.chunk_message_summary_repo import ChunkMessageSummaryRepository
from app.services.embedding_service import generate_embedding
from app.vector_store.qdrant_client import QdrantService
from app.core.config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def reindex_embeddings(
    batch_size: int = 100, dry_run: bool = False, group_id: Optional[int] = None
) -> None:
    """Re-index all embeddings with local model.

    Args:
        batch_size: Number of records to process in each batch
        dry_run: If True, don't actually update database/Qdrant
        group_id: If specified, only process this group
    """

    db = SessionLocal()
    repo = ChunkMessageSummaryRepository()
    qsvc = QdrantService()

    try:
        # Get total count
        logger.info("=" * 60)
        logger.info("Starting embedding re-indexing process")
        logger.info("=" * 60)
        logger.info(f"Configuration:")
        logger.info(f"  Embedding Provider: {settings.llm_embedding_provider}")
        logger.info(f"  Embedding Model: {settings.llm_embedding_model}")
        logger.info(f"  Batch Size: {batch_size}")
        logger.info(f"  Dry Run: {dry_run}")

        if group_id:
            logger.info(f"  Group ID Filter: {group_id}")
        logger.info("=" * 60)

        # Get all chunks
        if group_id:
            chunks = (
                db.query(ChunkMessageSummary)
                .filter(ChunkMessageSummary.group_id == group_id)
                .all()
            )
        else:
            chunks = db.query(ChunkMessageSummary).all()

        total_chunks = len(chunks)
        logger.info(f"Found {total_chunks} chunks to re-index")

        if total_chunks == 0:
            logger.warning("No chunks found. Nothing to do.")
            return

        # Process in batches
        processed = 0
        failed = 0
        skipped = 0

        for i in range(0, total_chunks, batch_size):
            batch = chunks[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_chunks + batch_size - 1) // batch_size

            logger.info(
                f"\n--- Processing batch {batch_num}/{total_batches} ({len(batch)} chunks) ---"
            )

            for chunk in batch:
                try:
                    # Check if chunk has content
                    if not chunk.message_content or not chunk.message_content.strip():
                        logger.warning(
                            f"  Skipping chunk {chunk.chunk_id}: empty content"
                        )
                        skipped += 1
                        continue

                    # Generate new embedding using local model
                    logger.debug(
                        f"  Generating embedding for chunk {chunk.chunk_id} (text_len={len(chunk.message_content)})"
                    )

                    if not dry_run:
                        # Generate embedding
                        embedding = generate_embedding(chunk.message_content)

                        # Generate new point ID
                        new_point_id = str(uuid.uuid4())

                        # Prepare metadata (matching the format in chunk_message_summary_service.py)
                        from datetime import timezone, timedelta

                        tz = timezone(timedelta(hours=8))

                        metadata = {
                            "created_at": (
                                chunk.created_at.replace(tzinfo=tz).isoformat()
                                if chunk.created_at
                                else None
                            ),
                            "date": (
                                chunk.start_time.date().isoformat()
                                if chunk.start_time
                                else None
                            ),
                            "end_time": (
                                chunk.end_time.replace(tzinfo=tz).isoformat()
                                if chunk.end_time
                                else None
                            ),
                            "group_id": chunk.group_id,
                            "start_time": (
                                chunk.start_time.replace(tzinfo=tz).isoformat()
                                if chunk.start_time
                                else None
                            ),
                            "summary_id": chunk.id,
                            "chunk_id": chunk.chunk_id,
                        }

                        # Upload to Qdrant
                        qsvc.client.upsert(
                            collection_name=qsvc.collection,
                            points=[
                                {
                                    "id": new_point_id,
                                    "vector": embedding,
                                    "payload": metadata,
                                }
                            ],
                        )

                        # Update database
                        chunk.qdrant_point_id = new_point_id
                        chunk.embedding = embedding
                        db.commit()

                        logger.info(
                            f"  ✓ Updated chunk {chunk.chunk_id} -> point_id: {new_point_id[:8]}..."
                        )
                    else:
                        logger.info(f"  [DRY-RUN] Would update chunk {chunk.chunk_id}")

                    processed += 1

                except Exception as e:
                    logger.error(f"  ✗ Failed to process chunk {chunk.chunk_id}: {e}")
                    failed += 1
                    db.rollback()
                    continue

            # Log progress
            progress = (i + len(batch)) / total_chunks * 100
            logger.info(
                f"Progress: {processed}/{total_chunks} ({progress:.1f}%) | Failed: {failed} | Skipped: {skipped}"
            )

        # Final summary
        logger.info("\n" + "=" * 60)
        logger.info("Re-indexing completed!")
        logger.info("=" * 60)
        logger.info(f"Total chunks: {total_chunks}")
        logger.info(f"Successfully processed: {processed}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Skipped: {skipped}")
        logger.info("=" * 60)

        if dry_run:
            logger.info("\n⚠️  This was a DRY RUN - no changes were made")

    except Exception as e:
        logger.exception(f"Fatal error during re-indexing: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Re-index all message embeddings with local model"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of records to process per batch (default: 100)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the process without making changes",
    )
    parser.add_argument(
        "--group-id", type=int, help="Only process chunks for this group ID"
    )

    args = parser.parse_args()

    try:
        reindex_embeddings(
            batch_size=args.batch_size, dry_run=args.dry_run, group_id=args.group_id
        )
    except KeyboardInterrupt:
        logger.warning("\n\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
