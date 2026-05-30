"""Application configuration / environment loader.

Settings are loaded from environment variables (and an optional .env file)
using pydantic-settings. This is the single source of truth for configuration
across the API and, in later milestones, the Celery workers and LangGraph jobs.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default RSS feeds focused on AI / tech news. Overridable via the RSS_FEEDS
# environment variable (JSON list).
DEFAULT_RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.wired.com/feed/tag/ai/latest/rss",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    app_name: str = Field(default="AI Weekly News Platform")
    environment: str = Field(default="local")
    debug: bool = Field(default=False)
    api_v1_prefix: str = Field(default="/api/v1")

    # --- PostgreSQL ---
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(default="ainews")
    postgres_password: str = Field(default="ainews")
    postgres_db: str = Field(default="ainews")

    # --- Redis ---
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)

    # --- AI providers (embeddings + LLM; used from Milestone 6 onward) ---
    # Active provider — currently Gemini free tier; switch to "openai" later.
    embedding_provider: str = Field(default="gemini")  # "gemini" | "openai"
    llm_provider: str = Field(default="gemini")  # "gemini" | "openai"

    # Shared vector dimension. Kept at 1536 so the pgvector column is
    # compatible across providers: Gemini's gemini-embedding-001 emits 1536 on
    # request, matching OpenAI's text-embedding-3-small (no migration on switch).
    embedding_dim: int = Field(default=1536)
    # Texts embedded per API call / DB commit during the embedding pipeline.
    embedding_batch_size: int = Field(default=100)
    # Max characters of article text sent to the embedding model.
    embedding_input_max_chars: int = Field(default=8000)

    # --- Deduplication (Milestone 7) ---
    # Max cosine distance for two articles to be considered the same story.
    # Lower = stricter. Tunable; 0.0 = identical, 1.0 = orthogonal.
    dedup_distance_threshold: float = Field(default=0.15)

    # --- Weekly clustering / report (Milestones 9–10) ---
    # Stories with last_seen_at within this many days count as "this week".
    weekly_window_days: int = Field(default=7)

    # Gemini (Google AI Studio free tier) — active now.
    gemini_api_key: str = Field(default="")
    gemini_embedding_model: str = Field(default="gemini-embedding-001")
    gemini_chat_model: str = Field(default="gemini-2.5-flash")

    # OpenAI — wired up for a later switch.
    openai_api_key: str = Field(default="")
    openai_embedding_model: str = Field(default="text-embedding-3-small")
    openai_chat_model: str = Field(default="gpt-4o-mini")

    # --- News providers (Milestone 4) ---
    news_query: str = Field(default="artificial intelligence")
    fetch_max_per_provider: int = Field(default=50)
    rss_feeds: list[str] = Field(default_factory=lambda: list(DEFAULT_RSS_FEEDS))
    newsapi_api_key: str = Field(default="")
    gnews_api_key: str = Field(default="")
    http_timeout_seconds: float = Field(default=15.0)

    @property
    def database_url(self) -> str:
        """libpq-style URL, used by psycopg directly (e.g. health check)."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sqlalchemy_database_url(self) -> str:
        """SQLAlchemy URL bound to the psycopg (v3) driver."""
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
