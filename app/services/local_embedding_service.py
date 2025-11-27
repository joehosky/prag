"""Local embedding service using sentence-transformers for Chinese text.

This service provides fast, local embedding generation without API calls.
Optimized for Traditional Chinese (繁體中文) support.
"""

from __future__ import annotations

import logging
import time
import warnings
from typing import List, Union, Optional

# Suppress transformers warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")
warnings.filterwarnings("ignore", message=".*BertSdpaSelfAttention.*")
warnings.filterwarnings("ignore", message=".*were not initialized.*")

logger = logging.getLogger(__name__)

# Lazy import to avoid loading model at module import time
_model_instance = None
_model_name = None


def get_local_embedding_model(model_name: str = "BAAI/bge-base-zh-v1.5"):
    """Get or create local embedding model instance.

    Supported models:
    - BAAI/bge-base-zh-v1.5 (recommended for Traditional Chinese)
    - shibing624/text2vec-base-chinese (faster, good for Chinese)
    - uer/sbert-base-chinese-nli (lightweight)

    Args:
        model_name: HuggingFace model identifier

    Returns:
        SentenceTransformer model instance
    """
    global _model_instance, _model_name

    # Return cached model if same name
    if _model_instance is not None and _model_name == model_name:
        return _model_instance

    try:
        from sentence_transformers import SentenceTransformer
        import os

        # Suppress tokenizers parallelism warnings
        os.environ["TOKENIZERS_PARALLELISM"] = "false"

        logger.info(f"Loading local embedding model: {model_name}")
        start_time = time.time()

        # Load model (will download on first use) with reduced verbosity
        import transformers

        transformers.logging.set_verbosity_error()

        _model_instance = SentenceTransformer(model_name, device="cpu")
        _model_name = model_name

        elapsed = time.time() - start_time
        logger.info(
            f"Local embedding model loaded: {model_name} in {elapsed:.2f}s, "
            f"embedding_dim={_model_instance.get_sentence_embedding_dimension()}"
        )

        return _model_instance

    except ImportError:
        logger.error(
            "sentence-transformers not installed. Install with: uv pip install sentence-transformers"
        )
        raise
    except Exception as e:
        logger.exception(f"Failed to load local embedding model {model_name}: {e}")
        raise


def generate_local_embedding(
    text: str,
    model_name: str = "BAAI/bge-base-zh-v1.5",
    normalize: bool = True,
) -> List[float]:
    """Generate embedding vector using local model.

    Args:
        text: Text to embed
        model_name: Model to use (default: jina-embeddings-v2-base-zh)
        normalize: Whether to L2-normalize embeddings (recommended for cosine similarity)

    Returns:
        List of floats (embedding vector)

    Example:
        >>> vector = generate_local_embedding("繁體中文測試")
        >>> len(vector)  # 768 for jina model
        768
    """
    start_time = time.time()

    try:
        model = get_local_embedding_model(model_name)

        # Generate embedding (with show_progress_bar=False to suppress progress bar)
        embedding = model.encode(
            text,
            normalize_embeddings=normalize,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        # Convert numpy array to list
        vector = embedding.tolist()

        elapsed = time.time() - start_time
        logger.debug(
            f"Local embedding generated: model={model_name} text_len={len(text)} "
            f"elapsed={elapsed*1000:.1f}ms vector_dim={len(vector)}"
        )

        return vector

    except Exception as e:
        elapsed = time.time() - start_time
        logger.exception(
            f"Local embedding generation failed: model={model_name} "
            f"elapsed={elapsed*1000:.1f}ms error={e}"
        )
        raise


async def agenerate_local_embedding(
    text: str,
    model_name: str = "BAAI/bge-base-zh-v1.5",
    normalize: bool = True,
) -> List[float]:
    """Async version of generate_local_embedding.

    Note: sentence-transformers is CPU-bound and not truly async.
    This wraps the sync call to maintain API compatibility.
    """
    import asyncio

    # Run in thread pool to avoid blocking event loop
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        generate_local_embedding,
        text,
        model_name,
        normalize,
    )


def generate_local_embeddings_batch(
    texts: List[str],
    model_name: str = "BAAI/bge-base-zh-v1.5",
    normalize: bool = True,
    batch_size: int = 32,
) -> List[List[float]]:
    """Generate embeddings for multiple texts in batch.

    More efficient than calling generate_local_embedding multiple times.

    Args:
        texts: List of texts to embed
        model_name: Model to use
        normalize: Whether to L2-normalize embeddings
        batch_size: Batch size for encoding (default: 32)

    Returns:
        List of embedding vectors
    """
    start_time = time.time()

    try:
        model = get_local_embedding_model(model_name)

        # Generate embeddings in batch
        embeddings = model.encode(
            texts,
            normalize_embeddings=normalize,
            convert_to_numpy=True,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 100,  # Show progress for large batches
        )

        # Convert numpy array to list of lists
        vectors = embeddings.tolist()

        elapsed = time.time() - start_time
        logger.info(
            f"Local embeddings batch generated: model={model_name} count={len(texts)} "
            f"elapsed={elapsed:.2f}s avg_per_text={elapsed/len(texts)*1000:.1f}ms"
        )

        return vectors

    except Exception as e:
        elapsed = time.time() - start_time
        logger.exception(
            f"Local embeddings batch generation failed: model={model_name} "
            f"count={len(texts)} elapsed={elapsed:.2f}s error={e}"
        )
        raise


__all__ = [
    "generate_local_embedding",
    "agenerate_local_embedding",
    "generate_local_embeddings_batch",
    "get_local_embedding_model",
]
