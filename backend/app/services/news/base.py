"""Adapter-pattern base class for news providers.

Each concrete provider (RSS, NewsAPI, GNews) implements `_fetch()` and returns
a list of `FetchedArticle`. `fetch()` wraps that call so a single failing
provider never aborts the whole batch.
"""

import logging
from abc import ABC, abstractmethod

from app.services.news.schemas import FetchedArticle

logger = logging.getLogger(__name__)


class NewsProvider(ABC):
    #: Stable identifier stored on each FetchedArticle ("rss"/"newsapi"/...).
    name: str = "base"

    @abstractmethod
    def _fetch(self, query: str, limit: int) -> list[FetchedArticle]:
        """Provider-specific fetch. May raise; `fetch()` handles errors."""
        raise NotImplementedError

    def fetch(self, query: str, limit: int) -> list[FetchedArticle]:
        """Fetch articles, isolating provider failures."""
        try:
            articles = self._fetch(query=query, limit=limit)
        except Exception:  # noqa: BLE001 - one provider must not break the rest
            logger.exception("Provider %r failed to fetch", self.name)
            return []
        logger.info("Provider %r fetched %d article(s)", self.name, len(articles))
        return articles
