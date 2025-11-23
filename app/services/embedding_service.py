from __future__ import annotations

import logging
from typing import List

from app.agents.llm_manager import get_llm_manager

logger = logging.getLogger(__name__)


def generate_embedding(
    text: str,
    timeout: int = 60,
    retries: int = 1,
    model: str | None = None,
) -> List[float]:
    """Generate embedding vector for `text` using LangChain LLMManager.

    Args:
        text: Text to embed
        timeout: Timeout (deprecated, LangChain handles internally)
        retries: Retries (deprecated, LangChain handles internally)
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
        manager = get_llm_manager()
        return manager.generate_embedding(text, model=model)
    except Exception as e:
        logger.exception("Embedding generation failed: %s", e)
        raise


async def agenerate_embedding(
    text: str,
    model: str | None = None,
) -> List[float]:
    """Async version of generate_embedding."""
    try:
        manager = get_llm_manager()
        return await manager.agenerate_embedding(text, model=model)
    except Exception as e:
        logger.exception("Async embedding generation failed: %s", e)
        raise


__all__ = ["generate_embedding", "agenerate_embedding"]
