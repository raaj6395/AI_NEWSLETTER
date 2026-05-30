"""Select the active embedding provider from settings."""

import logging

from app.core.config import Settings, get_settings
from app.services.embeddings.base import EmbeddingProvider
from app.services.embeddings.gemini import GeminiEmbeddingProvider
from app.services.embeddings.openai import OpenAIEmbeddingProvider

logger = logging.getLogger(__name__)


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    settings = settings or get_settings()

    if settings.embedding_provider == "openai":
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            dim=settings.embedding_dim,
        )
    if settings.embedding_provider == "gemini":
        return GeminiEmbeddingProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_embedding_model,
            dim=settings.embedding_dim,
        )
    raise ValueError(
        f"Unknown embedding_provider: {settings.embedding_provider!r}"
    )
