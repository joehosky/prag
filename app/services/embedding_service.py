from __future__ import annotations

import logging
from typing import List

from app.agents.llm_manager import get_llm_manager
from app.core.config import settings

logger = logging.getLogger(__name__)


def generate_embedding(
    text: str,
    model: str | None = None,
) -> List[float]:
    """Generate embedding vector for `text`.

    Automatically routes to local or OpenAI embedding based on LLM_EMBEDDING_PROVIDER setting.

    Args:
        text: Text to embed
        model: Embedding model to use (None = use default)

    Returns:
        List of floats (embedding vector)

    Example:
        >>> # Use default embedding model
        >>> vector = generate_embedding("Hello world")
        >>> # Use specific model
        >>> vector = generate_embedding(
        ...     "Hello world",
        ...     model="text-embedding-3-small"
        ... )
    """
    try:
        # Check if using local embedding
        provider = getattr(settings, "llm_embedding_provider", "openai")

        if provider == "local":
            from app.services.local_embedding_service import generate_local_embedding

            # Use configured model or default to jina for Chinese
            local_model = model or getattr(
                settings,
                "llm_embedding_model",
                "BAAI/bge-base-zh-v1.5",
            )
            return generate_local_embedding(text, local_model)
        else:
            # Use OpenAI via LLMManager
            manager = get_llm_manager()
            return manager.generate_embedding(text, model=model)

    except Exception as e:
        logger.exception("Embedding generation failed: %s", e)
        raise


async def agenerate_embedding(
    text: str,
    model: str | None = None,
) -> List[float]:
    """Async version of generate_embedding.

    Automatically routes to local or OpenAI embedding based on LLM_EMBEDDING_PROVIDER setting.
    """
    try:
        # Check if using local embedding
        provider = getattr(settings, "llm_embedding_provider", "openai")

        if provider == "local":
            from app.services.local_embedding_service import agenerate_local_embedding

            # Use configured model or default to jina for Chinese
            local_model = model or getattr(
                settings,
                "llm_embedding_model",
                "BAAI/bge-base-zh-v1.5",
            )
            return await agenerate_local_embedding(text, local_model)
        else:
            # Use OpenAI via LLMManager
            manager = get_llm_manager()
            return await manager.agenerate_embedding(text, model=model)

    except Exception as e:
        logger.exception("Async embedding generation failed: %s", e)
        raise


__all__ = ["generate_embedding", "agenerate_embedding"]
