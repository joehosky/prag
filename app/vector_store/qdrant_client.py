from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantService:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        api_key: Optional[str] = None,
        collection: Optional[str] = None,
    ) -> None:
        self.host = host or settings.qdrant_host
        self.port = port or settings.qdrant_port
        self.api_key = api_key or getattr(settings, "qdrant_api_key", None)
        self.collection = collection or settings.qdrant_collection_name
        self.client = QdrantClient(host=self.host, port=self.port, api_key=self.api_key)

    def add_points(self, points: List[Dict[str, Any]]) -> None:
        """Add points to Qdrant collection.

        `points` is a list of dicts with keys: id (str), vector (list[float]), payload (dict)
        """
        try:
            point_structs = []
            for p in points:
                pid = p.get("id")
                vector = p.get("vector")
                payload = p.get("payload")
                ps = qmodels.PointStruct(id=pid, vector=vector, payload=payload)
                point_structs.append(ps)

            if point_structs:
                self.client.upsert(
                    collection_name=self.collection, points=point_structs
                )
                logger.info(
                    "Qdrant: upserted %d points to collection %s",
                    len(point_structs),
                    self.collection,
                )
        except Exception:
            logger.exception("Qdrant: failed to add points")
            raise

    def delete_points(self, ids: List[str]) -> None:
        """Delete points by id (best-effort)."""
        try:
            if not ids:
                return
            selector = qmodels.PointIdsList(points=ids)
            self.client.delete(
                collection_name=self.collection, points_selector=selector
            )
            logger.info(
                "Qdrant: deleted %d points from collection %s",
                len(ids),
                self.collection,
            )
        except Exception:
            logger.exception("Qdrant: failed to delete points")
            raise


__all__ = ["QdrantService"]
