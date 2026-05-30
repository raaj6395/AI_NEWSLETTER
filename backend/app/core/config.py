"""Application configuration / environment loader.

Settings are loaded from environment variables (and an optional .env file)
using pydantic-settings. This is the single source of truth for configuration
across the API and, in later milestones, the Celery workers and LangGraph jobs.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # --- OpenAI (used from Milestone 6 onward) ---
    openai_api_key: str = Field(default="")

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
