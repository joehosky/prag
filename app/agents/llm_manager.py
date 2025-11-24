"""Unified LLM manager using LangChain"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Union

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMManager:
    """Centralized LLM management through LangChain.

    Supports:
    - Multiple models from same provider (e.g., gpt-4o, gpt-4o-mini)
    - Text generation (chat completion)
    - Embedding generation
    - Async operations

    Example:
        >>> manager = LLMManager()
        >>> # Use default model
        >>> response = manager.invoke("Hello")
        >>> # Use specific model
        >>> response = manager.invoke("Complex task", model="gpt-4o")
        >>> # Generate embedding
        >>> vector = manager.generate_embedding("text to embed")
    """

    def __init__(
        self,
        default_model: Optional[str] = None,
        default_embedding_model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4000,
        provider: str = "openai",
    ):
        """Initialize LLM Manager.

        Args:
            default_model: Default chat model
            default_embedding_model: Default embedding model
            temperature: Default temperature
            max_tokens: Default max tokens
            provider: LLM provider (openai, gemini, etc.)
        """
        self.default_model = default_model or settings.openai_model
        self.default_embedding_model = (
            default_embedding_model or settings.openai_embedding_model
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.provider = provider

        # Cache for LLM instances
        self._llm_cache: Dict[str, Any] = {}
        self._embedding_cache: Dict[str, Any] = {}

    def _get_llm(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """Get or create LLM instance for specific model."""
        model = model or self.default_model
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        # Cache key
        cache_key = f"{model}_{temp}_{tokens}"

        if cache_key not in self._llm_cache:
            if self.provider == "openai":
                self._llm_cache[cache_key] = ChatOpenAI(
                    model=model,
                    temperature=temp,
                    max_tokens=tokens,
                    openai_api_key=settings.openai_api_key,
                )
            elif self.provider == "gemini":
                from langchain_google_genai import ChatGoogleGenerativeAI

                self._llm_cache[cache_key] = ChatGoogleGenerativeAI(
                    model=model,
                    temperature=temp,
                    max_output_tokens=tokens,
                    google_api_key=settings.gemini_api_key,
                )
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        return self._llm_cache[cache_key]

    def _get_embeddings(self, model: Optional[str] = None):
        """Get or create Embeddings instance."""
        model = model or self.default_embedding_model

        if model not in self._embedding_cache:
            self._embedding_cache[model] = OpenAIEmbeddings(
                model=model,
                openai_api_key=settings.openai_api_key,
            )

        return self._embedding_cache[model]

    def llm(self):
        return self._get_llm()

    def get_llm_for_agent(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        return self._get_llm(model, temperature, max_tokens)

    def invoke(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Invoke LLM with prompt."""
        start_time = time.time()
        effective_model = model or self.default_model
        prompt_preview = (
            prompt[:80].replace("\n", " ") + "..."
            if len(prompt) > 80
            else prompt.replace("\n", " ")
        )

        logger.debug(
            "LLMManager:invoke:start model=%s prompt_len=%d prompt=%s",
            effective_model,
            len(prompt),
            prompt_preview,
        )

        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))

        llm = self._get_llm(model, temperature, max_tokens)

        try:
            response = llm.invoke(messages)
            elapsed = time.time() - start_time
            response_len = len(response.content) if response.content else 0

            logger.debug(
                "LLMManager:invoke:completed model=%s elapsed=%.2fs response_len=%d",
                effective_model,
                elapsed,
                response_len,
            )
            return response.content
        except Exception as e:
            elapsed = time.time() - start_time
            logger.exception(
                "LLMManager:invoke:failed model=%s elapsed=%.2fs error=%s",
                effective_model,
                elapsed,
                e,
            )
            raise

    async def ainvoke(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Async version of invoke."""
        start_time = time.time()
        effective_model = model or self.default_model
        prompt_preview = (
            prompt[:80].replace("\n", " ") + "..."
            if len(prompt) > 80
            else prompt.replace("\n", " ")
        )

        logger.debug(
            "LLMManager:ainvoke:start model=%s prompt_len=%d prompt=%s",
            effective_model,
            len(prompt),
            prompt_preview,
        )

        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))

        llm = self._get_llm(model, temperature, max_tokens)

        try:
            response = await llm.ainvoke(messages)
            elapsed = time.time() - start_time
            response_len = len(response.content) if response.content else 0

            logger.debug(
                "LLMManager:ainvoke:completed model=%s elapsed=%.2fs response_len=%d",
                effective_model,
                elapsed,
                response_len,
            )
            return response.content
        except Exception as e:
            elapsed = time.time() - start_time
            logger.exception(
                "LLMManager:ainvoke:failed model=%s elapsed=%.2fs error=%s",
                effective_model,
                elapsed,
                e,
            )
            raise

    def generate_embedding(
        self,
        text: Union[str, List[str]],
        model: Optional[str] = None,
    ) -> Union[List[float], List[List[float]]]:
        """Generate embedding vector(s) for text."""
        start_time = time.time()
        effective_model = model or self.default_embedding_model

        if isinstance(text, str):
            text_preview = (
                text[:50].replace("\n", " ") + "..."
                if len(text) > 50
                else text.replace("\n", " ")
            )
            text_count = 1
        else:
            text_preview = f"[{len(text)} texts]"
            text_count = len(text)

        logger.debug(
            "LLMManager:generate_embedding:start model=%s count=%d text=%s",
            effective_model,
            text_count,
            text_preview,
        )

        embeddings = self._get_embeddings(model)

        try:
            if isinstance(text, str):
                vector = embeddings.embed_query(text)
                elapsed = time.time() - start_time
                logger.debug(
                    "LLMManager:generate_embedding:completed model=%s elapsed=%.2fs vector_dim=%d",
                    effective_model,
                    elapsed,
                    len(vector),
                )
                return vector
            else:
                vectors = embeddings.embed_documents(text)
                elapsed = time.time() - start_time
                logger.debug(
                    "LLMManager:generate_embedding:completed model=%s elapsed=%.2fs vectors_count=%d vector_dim=%d",
                    effective_model,
                    elapsed,
                    len(vectors),
                    len(vectors[0]) if vectors else 0,
                )
                return vectors
        except Exception as e:
            elapsed = time.time() - start_time
            logger.exception(
                "LLMManager:generate_embedding:failed model=%s elapsed=%.2fs error=%s",
                effective_model,
                elapsed,
                e,
            )
            raise

    async def agenerate_embedding(
        self,
        text: Union[str, List[str]],
        model: Optional[str] = None,
    ) -> Union[List[float], List[List[float]]]:
        """Async version of generate_embedding."""
        start_time = time.time()
        effective_model = model or self.default_embedding_model

        if isinstance(text, str):
            text_preview = (
                text[:50].replace("\n", " ") + "..."
                if len(text) > 50
                else text.replace("\n", " ")
            )
            text_count = 1
        else:
            text_preview = f"[{len(text)} texts]"
            text_count = len(text)

        logger.debug(
            "LLMManager:agenerate_embedding:start model=%s count=%d text=%s",
            effective_model,
            text_count,
            text_preview,
        )

        embeddings = self._get_embeddings(model)

        try:
            if isinstance(text, str):
                vector = await embeddings.aembed_query(text)
                elapsed = time.time() - start_time
                logger.debug(
                    "LLMManager:agenerate_embedding:completed model=%s elapsed=%.2fs vector_dim=%d",
                    effective_model,
                    elapsed,
                    len(vector),
                )
                return vector
            else:
                vectors = await embeddings.aembed_documents(text)
                elapsed = time.time() - start_time
                logger.debug(
                    "LLMManager:agenerate_embedding:completed model=%s elapsed=%.2fs vectors_count=%d vector_dim=%d",
                    effective_model,
                    elapsed,
                    len(vectors),
                    len(vectors[0]) if vectors else 0,
                )
                return vectors
        except Exception as e:
            elapsed = time.time() - start_time
            logger.exception(
                "LLMManager:agenerate_embedding:failed model=%s elapsed=%.2fs error=%s",
                effective_model,
                elapsed,
                e,
            )
            raise


# Global singleton for convenience
_default_manager: Optional[LLMManager] = None


def get_llm_manager() -> LLMManager:
    """Get or create singleton default LLM manager."""
    global _default_manager
    if _default_manager is None:
        # _default_manager = LLMManager(
        #     default_model="gemini-2.0-flash",
        #     default_embedding_model="text-embedding-3-small",
        #     provider="gemini",
        # )
        _default_manager = LLMManager(
            default_model="gpt-4.1-mini",
            default_embedding_model="text-embedding-3-small",
            provider="openai",
        )
    return _default_manager
