"""GNews provider (https://gnews.io/docs/v4#search-endpoint)."""

import logging

import httpx

from app.services.news.base import NewsProvider
from app.services.news.parsing import from_iso
from app.services.news.schemas import FetchedArticle

logger = logging.getLogger(__name__)


class GNewsProvider(NewsProvider):
    name = "gnews"
    ENDPOINT = "https://gnews.io/api/v4/search"

    def __init__(self, api_key: str, timeout: float = 15.0):
        self.api_key = api_key
        self.timeout = timeout

    def _fetch(self, query: str, limit: int) -> list[FetchedArticle]:
        params = {
            "q": query,
            "lang": "en",
            "max": min(limit, 100),  # GNews max per request
            "apikey": self.api_key,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(self.ENDPOINT, params=params)
            resp.raise_for_status()
            payload = resp.json()

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
                    source=(item.get("source") or {}).get("name") or "GNews",
                    provider=self.name,
                    description=item.get("description"),
                    content=item.get("content"),
                    url_to_image=item.get("image"),
                    published_at=from_iso(item.get("publishedAt")),
                    raw=item,
                )
            )
        return results
