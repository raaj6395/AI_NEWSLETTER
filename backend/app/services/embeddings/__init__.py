"""Embedding providers — provider-agnostic vector generation.

    get_embedding_provider()  — active provider from settings (Gemini/OpenAI)
    EmbeddingProvider         — base class producing unit-normalized vectors
"""

from app.services.embeddings.base import EmbeddingProvider, l2_normalize
from app.services.embeddings.factory import get_embedding_provider

__all__ = ["EmbeddingProvider", "l2_normalize", "get_embedding_provider"]
