"""Unified LLM manager using LangChain"""

from __future__ import annotations

import logging
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
            # increase new provider for future expansion
            # elif self.provider == "gemini":
            #     from langchain_google_genai import ChatGoogleGenerativeAI
            #     self._llm_cache[cache_key] = ChatGoogleGenerativeAI(
            #         model=model,
            #         temperature=temp,
            #         max_output_tokens=tokens,
            #         google_api_key=settings.gemini_api_key,
            #     )
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

        return self._llm_cache[cache_key]

    def _get_embeddings(self, model: Optional[str] = None):
        """Get or create Embeddings instance."""
        model = model or self.default_embedding_model

        if model not in self._embedding_cache:
            if self.provider == "openai":
                self._embedding_cache[model] = OpenAIEmbeddings(
                    model=model,
                    openai_api_key=settings.openai_api_key,
                )
            # increase new provider for future expansion
            # elif self.provider == "gemini":
            #     from langchain_google_genai import GoogleGenerativeAIEmbeddings
            #     self._embedding_cache[model] = GoogleGenerativeAIEmbeddings(
            #         model=model,
            #         google_api_key=settings.gemini_api_key,
            #     )
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

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
        """Invoke LLM with prompt.

        Args:
            prompt: User prompt
            system_message: Optional system message
            model: Model to use (None = use default)
            temperature: Temperature override
            max_tokens: Max tokens override
            **kwargs: Additional parameters

        Returns:
            LLM response text

        Example:
            >>> manager = LLMManager()
            >>> # Use default model (gpt-4o-mini)
            >>> response = manager.invoke("Simple question")
            >>> # Use gpt-4o for complex task
            >>> response = manager.invoke(
            ...     "Complex reasoning task",
            ...     model="gpt-4o",
            ...     temperature=0.7
            ... )
        """
        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))

        llm = self._get_llm(model, temperature, max_tokens)

        try:
            response = llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.exception(
                "LLM invocation failed: model=%s, error=%s",
                model or self.default_model,
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
        """Async version of invoke.

        Args:
            prompt: User prompt
            system_message: Optional system message
            model: Model to use (None = use default)
            temperature: Temperature override
            max_tokens: Max tokens override
            **kwargs: Additional parameters

        Returns:
            LLM response text
        """
        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))

        llm = self._get_llm(model, temperature, max_tokens)

        try:
            response = await llm.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.exception(
                "LLM async invocation failed: model=%s, error=%s",
                model or self.default_model,
                e,
            )
            raise

    def generate_embedding(
        self,
        text: Union[str, List[str]],
        model: Optional[str] = None,
    ) -> Union[List[float], List[List[float]]]:
        """Generate embedding vector(s) for text.

        Args:
            text: Single text or list of texts
            model: Embedding model to use (None = use default)

        Returns:
            Single vector (if text is str) or list of vectors (if text is list)

        Example:
            >>> manager = LLMManager()
            >>> # Single text
            >>> vector = manager.generate_embedding("Hello world")
            >>> len(vector)  # 1536 for text-embedding-3-small 1536
            >>> # Batch texts
            >>> vectors = manager.generate_embedding(["Text 1", "Text 2"])
            >>> len(vectors) 2
        """
        embeddings = self._get_embeddings(model)

        try:
            if isinstance(text, str):
                # Single text
                vector = embeddings.embed_query(text)
                return vector
            else:
                # Batch texts
                vectors = embeddings.embed_documents(text)
                return vectors
        except Exception as e:
            logger.exception(
                "Embedding generation failed: model=%s, error=%s",
                model or self.default_embedding_model,
                e,
            )
            raise

    async def agenerate_embedding(
        self,
        text: Union[str, List[str]],
        model: Optional[str] = None,
    ) -> Union[List[float], List[List[float]]]:
        """Async version of generate_embedding.

        Args:
            text: Single text or list of texts
            model: Embedding model to use (None = use default)

        Returns:
            Single vector (if text is str) or list of vectors (if text is list)
        """
        embeddings = self._get_embeddings(model)

        try:
            if isinstance(text, str):
                vector = await embeddings.aembed_query(text)
                return vector
            else:
                vectors = await embeddings.aembed_documents(text)
                return vectors
        except Exception as e:
            logger.exception(
                "Async embedding generation failed: model=%s, error=%s",
                model or self.default_embedding_model,
                e,
            )
            raise


# Global singleton for convenience
_default_manager: Optional[LLMManager] = None


def get_llm_manager() -> LLMManager:
    """Get or create singleton default LLM manager."""
    global _default_manager
    if _default_manager is None:
        _default_manager = LLMManager()
    return _default_manager


__all__ = ["LLMManager", "get_llm_manager"]
