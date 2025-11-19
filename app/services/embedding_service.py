from __future__ import annotations

import time
import logging
from typing import List, Optional

import openai

from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_embedding(text: str, timeout: int = 60, retries: int = 1) -> List[float]:
    """Generate embedding vector for `text` using OpenAI Embeddings API.

    Returns a list of floats.
    """
    api_key = settings.openai_api_key
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured in settings")
    openai.api_key = api_key

    model = settings.openai_embedding_model

    attempt = 0
    backoff = 0.5
    while True:
        try:
            resp = openai.Embedding.create(
                input=text, model=model, request_timeout=timeout
            )
            # typical response: {'data': [{'embedding': [...]}], ...}
            if resp and "data" in resp and len(resp.data) > 0:
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
