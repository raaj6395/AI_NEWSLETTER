"""OpenAI embedding provider — wired for a later switch from Gemini.

Requires the `openai` package and OPENAI_API_KEY. The import is lazy so the
embeddings package works on the Gemini path without `openai` installed; add
`openai` to requirements when switching `embedding_provider` to "openai".
"""

import logging

from app.services.embeddings.base import EmbeddingProvider, l2_normalize

logger = logging.getLogger(__name__)

_MAX_PER_REQUEST = 100


class OpenAIEmbeddingProvider(EmbeddingProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str, dim: int):
        super().__init__(model=model, dim=dim)
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        vectors: list[list[float]] = []
        for start in range(0, len(texts), _MAX_PER_REQUEST):
            chunk = texts[start : start + _MAX_PER_REQUEST]
            resp = self._client.embeddings.create(
                model=self.model, input=chunk, dimensions=self.dim
            )
            vectors.extend(l2_normalize(list(d.embedding)) for d in resp.data)

        self._validate(vectors, expected=len(texts))
        return vectors
