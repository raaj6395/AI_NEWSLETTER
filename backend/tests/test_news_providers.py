"""Tests for the Milestone 4 news source framework (offline / no network)."""

from app.core.config import Settings
from app.services.news import RSSProvider
from app.services.news.base import NewsProvider
from app.services.news.registry import build_providers

SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>First AI story</title>
      <link>https://example.com/a</link>
      <description>Summary A</description>
      <pubDate>Mon, 26 May 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Second AI story</title>
      <link>https://example.com/b</link>
      <description>Summary B</description>
      <pubDate>Tue, 27 May 2026 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""


def test_rss_provider_parses_feed(monkeypatch):
    import feedparser

    parsed = feedparser.parse(SAMPLE_RSS)
    monkeypatch.setattr(feedparser, "parse", lambda url: parsed)

    provider = RSSProvider(feeds=["http://unused"])
    articles = provider.fetch(query="ai", limit=10)

    assert len(articles) == 2
    first = articles[0]
    assert first.url == "https://example.com/a"
    assert first.title == "First AI story"
    assert first.source == "Test Feed"
    assert first.provider == "rss"
    assert first.published_at is not None
    assert first.published_at.tzinfo is not None


def test_build_providers_enables_by_config():
    # Only RSS when no API keys are configured.
    only_rss = Settings(
        rss_feeds=["http://f"], newsapi_api_key="", gnews_api_key=""
    )
    assert [p.name for p in build_providers(only_rss)] == ["rss"]

    # NewsAPI and GNews switch on when their keys are present.
    all_on = Settings(
        rss_feeds=["http://f"], newsapi_api_key="k1", gnews_api_key="k2"
    )
    assert [p.name for p in build_providers(all_on)] == ["rss", "newsapi", "gnews"]

    # No RSS feeds -> RSS disabled.
    no_rss = Settings(rss_feeds=[], newsapi_api_key="k1")
    assert [p.name for p in build_providers(no_rss)] == ["newsapi"]


def test_provider_failure_is_isolated():
    class BoomProvider(NewsProvider):
        name = "boom"

        def _fetch(self, query: str, limit: int):
            raise RuntimeError("provider exploded")

    # fetch() must swallow the error and return an empty list.
    assert BoomProvider().fetch(query="ai", limit=5) == []
