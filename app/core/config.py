"""
Application Configuration
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/line_rag_db"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "line_messages"

    # OpenAI API Key
    openai_api_key: str = ""

    # Gemini API Key
    gemini_api_key: str = ""

    # LLM Configuration
    llm_provider: str = "openai"
    llm_model: str = "gpt-4.1-mini"
    llm_embedding_provider: str = "openai"
    llm_embedding_model: str = "text-embedding-3-small"
    llm_keep_memory: bool = False
    llm_keep_memory_limit: int = 3

    # Application
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8200

    # Logging
    log_level: str = "INFO"
    log_console: bool = True
    log_console_level: Optional[str] = None
    log_file: bool = False
    log_file_level: Optional[str] = None
    log_dir: str = "logs"
    log_retention_days: int = 7

    # Score Fusion Weights
    score_weight_alpha: float = 0.5  # Cosine similarity
    score_weight_beta: float = 0.3  # BM25
    score_weight_gamma: float = 0.2  # Recency boost
    score_threshold: float = 0.3

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }


settings = Settings()
