"""RSS / Atom feed provider.

Reads a configured list of feed URLs with feedparser. Requires no API key,
so this is the always-available provider used to validate Milestone 4.
"""

import logging
from urllib.parse import urlparse

import feedparser

from app.services.news.base import NewsProvider
from app.services.news.parsing import from_struct_time
from app.services.news.schemas import FetchedArticle

logger = logging.getLogger(__name__)


class RSSProvider(NewsProvider):
    name = "rss"

    def __init__(self, feeds: list[str]):
        self.feeds = feeds

    def _fetch(self, query: str, limit: int) -> list[FetchedArticle]:
        articles: list[FetchedArticle] = []
        for feed_url in self.feeds:
            articles.extend(self._fetch_feed(feed_url, limit))
        return articles

    def _fetch_feed(self, feed_url: str, limit: int) -> list[FetchedArticle]:
        parsed = feedparser.parse(feed_url)
        if parsed.bozo and not parsed.entries:
            logger.warning(
                "RSS feed %s failed to parse: %s", feed_url, parsed.get("bozo_exception")
            )
            return []

        outlet = parsed.feed.get("title") or urlparse(feed_url).netloc
        results: list[FetchedArticle] = []
        for entry in parsed.entries[:limit]:
            link = entry.get("link")
            title = entry.get("title")
            if not link or not title:
                continue
            results.append(
                FetchedArticle(
                    url=link,
                    title=title,
                    source=outlet,
                    provider=self.name,
                    author=entry.get("author"),
                    description=entry.get("summary"),
                    content=self._extract_content(entry),
                    published_at=from_struct_time(entry.get("published_parsed"))
                    or from_struct_time(entry.get("updated_parsed")),
                    raw=dict(entry),
                )
            )
        return results

    @staticmethod
    def _extract_content(entry) -> str | None:
        content = entry.get("content")
        if content and isinstance(content, list) and content:
            return content[0].get("value")
        return entry.get("summary")
