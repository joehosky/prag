from __future__ import annotations

import time
import logging
from typing import List, Optional

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_embedding(text: str, timeout: int = 60, retries: int = 1) -> List[float]:
    """Generate embedding vector for `text` using OpenAI Embeddings API.

    Returns a list of floats.
    """
    api_key = settings.openai_api_key
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured in settings")

    model = settings.openai_embedding_model
    client = OpenAI(api_key=api_key)

    attempt = 0
    backoff = 0.5
    while True:
        try:
            resp = client.embeddings.create(input=text, model=model, timeout=timeout)
            # response.data is a list of objects with .embedding
            if resp and getattr(resp, "data", None) and len(resp.data) > 0:
                emb = resp.data[0].embedding
                return [float(x) for x in emb]
            raise RuntimeError("No embedding returned from API")
        except Exception as e:
            attempt += 1
            logger.exception(
                "Embedding generation failed on attempt %d: %s", attempt, e
            )
            if attempt > retries:
                raise
            time.sleep(backoff)
            backoff *= 2


__all__ = ["generate_embedding"]
