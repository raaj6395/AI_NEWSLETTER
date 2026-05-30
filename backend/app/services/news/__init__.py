"""News source framework — adapter-pattern providers and aggregation.

Public entry points:
    fetch_news()       — run all enabled providers and aggregate results
    build_providers()  — instantiate enabled providers from settings
    FetchedArticle     — normalized article shape produced by every provider
"""

from app.services.news.base import NewsProvider
from app.services.news.gnews import GNewsProvider
from app.services.news.newsapi import NewsAPIProvider
from app.services.news.registry import build_providers, fetch_news
from app.services.news.rss import RSSProvider
from app.services.news.schemas import FetchedArticle

__all__ = [
    "FetchedArticle",
    "NewsProvider",
    "RSSProvider",
    "NewsAPIProvider",
    "GNewsProvider",
    "build_providers",
    "fetch_news",
]
