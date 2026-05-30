"""Tests for the Milestone 6 embedding pipeline (offline / no network)."""

from app.core.config import Settings, get_settings
from app.db.base import SessionLocal
from app.models import Article
from app.services.embeddings.base import EmbeddingProvider, l2_normalize
from app.services.embeddings.factory import get_embedding_provider
from app.services.embeddings.gemini import GeminiEmbeddingProvider
from app.services.embedding_pipeline import build_embedding_input, embed_articles

_TEST_SOURCE = "embed-test-source"


class FakeProvider(EmbeddingProvider):
    """Deterministic provider that avoids any network call."""

    name = "fake"

    def __init__(self, dim: int):
        super().__init__(model="fake", dim=dim)

    def embed_texts(self, texts):
        # First component varies with text length so vectors differ.
        vectors = []
        for i, t in enumerate(texts):
            v = [0.0] * self.dim
            v[0] = float(len(t) + i + 1)
            vectors.append(l2_normalize(v))
        return vectors


def test_l2_normalize_unit_length():
    out = l2_normalize([3.0, 4.0])
    assert abs((out[0] ** 2 + out[1] ** 2) ** 0.5 - 1.0) < 1e-9
    assert l2_normalize([0.0, 0.0]) == [0.0, 0.0]  # zero vector is a no-op


def test_build_embedding_input_truncates():
    art = Article(url="u", title="Title", source="s", description="d" * 100)
    text = build_embedding_input(art, max_chars=20)
    assert len(text) == 20
    assert text.startswith("Title")


def test_factory_defaults_to_gemini():
    provider = get_embedding_provider(
        Settings(embedding_provider="gemini", gemini_api_key="dummy")
    )
    assert isinstance(provider, GeminiEmbeddingProvider)
    assert provider.dim == get_settings().embedding_dim


def test_embed_articles_fills_vectors():
    db = SessionLocal()
    dim = get_settings().embedding_dim
    try:
        db.query(Article).filter(Article.source == _TEST_SOURCE).delete()
        db.commit()
        db.add_all(
            [
                Article(url="https://embed-test/1", title="A", source=_TEST_SOURCE),
                Article(url="https://embed-test/2", title="BB", source=_TEST_SOURCE),
            ]
        )
        db.commit()

        rows = db.query(Article).filter(Article.source == _TEST_SOURCE).all()
        assert all(r.embedding is None for r in rows)

        result = embed_articles(db, rows, provider=FakeProvider(dim))
        assert result.pending == 2
        assert result.embedded == 2
        assert result.failed == 0

        for r in rows:
            db.refresh(r)
            assert r.embedding is not None
            assert len(r.embedding) == dim
    finally:
        db.query(Article).filter(Article.source == _TEST_SOURCE).delete()
        db.commit()
        db.close()
