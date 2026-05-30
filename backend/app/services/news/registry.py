"""Provider registry and the `fetch_news()` aggregation entry point.

Providers are built from application settings: RSS is enabled whenever feeds
are configured, while NewsAPI and GNews are enabled only when their API keys
are present. `fetch_news()` runs every enabled provider and returns the
combined, de-duplicated-by-URL list of `FetchedArticle`.
"""

import logging

from app.core.config import Settings, get_settings
from app.services.news.base import NewsProvider
from app.services.news.gnews import GNewsProvider
from app.services.news.newsapi import NewsAPIProvider
from app.services.news.rss import RSSProvider
from app.services.news.schemas import FetchedArticle

logger = logging.getLogger(__name__)


def build_providers(settings: Settings | None = None) -> list[NewsProvider]:
    """Instantiate the providers enabled by the current configuration."""
    settings = settings or get_settings()
    providers: list[NewsProvider] = []

    if settings.rss_feeds:
        providers.append(RSSProvider(feeds=settings.rss_feeds))
    if settings.newsapi_api_key:
        providers.append(
            NewsAPIProvider(
                api_key=settings.newsapi_api_key,
                timeout=settings.http_timeout_seconds,
            )
        )
    if settings.gnews_api_key:
        providers.append(
            GNewsProvider(
                api_key=settings.gnews_api_key,
                timeout=settings.http_timeout_seconds,
            )
        )

    logger.info(
        "Enabled news providers: %s", [p.name for p in providers] or "none"
    )
    return providers


def fetch_news(
    query: str | None = None,
    limit_per_provider: int | None = None,
    settings: Settings | None = None,
) -> list[FetchedArticle]:
    """Fetch and aggregate articles from all enabled providers.

    Duplicate URLs across providers are collapsed, keeping the first seen.
    """
    settings = settings or get_settings()
    query = query or settings.news_query
    limit = limit_per_provider or settings.fetch_max_per_provider

    seen_urls: set[str] = set()
    aggregated: list[FetchedArticle] = []
    for provider in build_providers(settings):
        for article in provider.fetch(query=query, limit=limit):
            if article.url in seen_urls:
                continue
            seen_urls.add(article.url)
            aggregated.append(article)

    logger.info("fetch_news aggregated %d unique article(s)", len(aggregated))
    return aggregated
