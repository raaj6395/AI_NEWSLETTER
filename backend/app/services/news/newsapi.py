"""NewsAPI.org provider (https://newsapi.org/docs/endpoints/everything)."""

import logging

import httpx

from app.services.news.base import NewsProvider
from app.services.news.parsing import from_iso
from app.services.news.schemas import FetchedArticle

logger = logging.getLogger(__name__)


class NewsAPIProvider(NewsProvider):
    name = "newsapi"
    ENDPOINT = "https://newsapi.org/v2/everything"

    def __init__(self, api_key: str, timeout: float = 15.0):
        self.api_key = api_key
        self.timeout = timeout

    def _fetch(self, query: str, limit: int) -> list[FetchedArticle]:
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": min(limit, 100),  # NewsAPI hard cap
            "apiKey": self.api_key,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(self.ENDPOINT, params=params)
            resp.raise_for_status()
            payload = resp.json()

        if payload.get("status") != "ok":
            logger.warning("NewsAPI error: %s", payload.get("message"))
            return []

        results: list[FetchedArticle] = []
        for item in payload.get("articles", [])[:limit]:
            url = item.get("url")
            title = item.get("title")
            if not url or not title:
                continue
            results.append(
                FetchedArticle(
                    url=url,
                    title=title,
                    source=(item.get("source") or {}).get("name") or "NewsAPI",
                    provider=self.name,
                    author=item.get("author"),
                    description=item.get("description"),
                    content=item.get("content"),
                    url_to_image=item.get("urlToImage"),
                    published_at=from_iso(item.get("publishedAt")),
                    raw=item,
                )
            )
        return results
