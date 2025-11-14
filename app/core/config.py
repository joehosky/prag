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

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4"
    openai_embedding_model: str = "text-embedding-3-small"

    # Application
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

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
