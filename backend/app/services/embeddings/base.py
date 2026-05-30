"""Embedding provider abstraction.

Providers turn a list of texts into a list of unit-normalized vectors of a
fixed dimension. Concrete providers (Gemini now, OpenAI later) are selected by
the `embedding_provider` setting via `factory.get_embedding_provider()`.
"""

import math
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    #: Stable identifier ("gemini" | "openai").
    name: str = "base"

    def __init__(self, model: str, dim: int):
        self.model = model
        self.dim = dim

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, aligned by index."""
        raise NotImplementedError

    def _validate(self, vectors: list[list[float]], expected: int) -> None:
        if len(vectors) != expected:
            raise ValueError(
                f"{self.name}: expected {expected} vectors, got {len(vectors)}"
            )
        for vec in vectors:
            if len(vec) != self.dim:
                raise ValueError(
                    f"{self.name}: expected dim {self.dim}, got {len(vec)}"
                )


def l2_normalize(vec: list[float]) -> list[float]:
    """Scale a vector to unit length (no-op for a zero vector).

    Gemini recommends normalizing embeddings when the output dimensionality is
    not the native 3072; cosine ranking is unaffected and it keeps cosine/L2
    consistent in pgvector.
    """
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]
