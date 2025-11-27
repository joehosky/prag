"""
Initialize Qdrant Vector Database
"""

import sys
import os
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import settings


def init_qdrant():
    """Initialize Qdrant collections"""
    print("Initializing Qdrant...")
    print(f"Qdrant host: {settings.qdrant_host}:{settings.qdrant_port}")

    try:
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

        # Create collection for LINE messages
        collection_name = settings.qdrant_collection_name

        # Check if collection exists
        collections = client.get_collections()
        if any(col.name == collection_name for col in collections.collections):
            print(f"Collection '{collection_name}' already exists")
            client.delete_collection(collection_name=collection_name)
            print(f"Deleted existing collection '{collection_name}'")

        # Create new collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=768,
                distance=Distance.COSINE,  # BAAI/bge-base-zh-v1.5 embedding dimension
                # size=1536, distance=Distance.COSINE  # OpenAI embedding dimension
            ),
        )
        print(f"✓ Qdrant collection '{collection_name}' initialized successfully!")

    except Exception as e:
        print(f"✗ Error initializing Qdrant: {e}")
        print("Please make sure Qdrant is running.")
        return False

    return True


if __name__ == "__main__":
    success = init_qdrant()
    sys.exit(0 if success else 1)
