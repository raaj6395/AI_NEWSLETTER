"""Gemini embedding provider (Google AI Studio free tier).

Uses the google-genai SDK's `embed_content` with an explicit
`output_dimensionality` so vectors match the configured `embedding_dim`
(1536) — keeping the pgvector column compatible with a future OpenAI switch.
"""

import logging

from app.services.embeddings.base import EmbeddingProvider, l2_normalize

logger = logging.getLogger(__name__)

# embed_content accepts a limited number of items per request.
_MAX_PER_REQUEST = 100


class GeminiEmbeddingProvider(EmbeddingProvider):
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        dim: int,
        task_type: str = "SEMANTIC_SIMILARITY",
    ):
        super().__init__(model=model, dim=dim)
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        # Imported lazily so the package loads even without the SDK installed.
        from google import genai

        self._genai = genai
        self._client = genai.Client(api_key=api_key)
        self.task_type = task_type

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        from google.genai import types

        config = types.EmbedContentConfig(
            task_type=self.task_type,
            output_dimensionality=self.dim,
        )

        vectors: list[list[float]] = []
        for start in range(0, len(texts), _MAX_PER_REQUEST):
            chunk = texts[start : start + _MAX_PER_REQUEST]
            resp = self._client.models.embed_content(
                model=self.model, contents=chunk, config=config
            )
            vectors.extend(l2_normalize(list(e.values)) for e in resp.embeddings)

        self._validate(vectors, expected=len(texts))
        return vectors
