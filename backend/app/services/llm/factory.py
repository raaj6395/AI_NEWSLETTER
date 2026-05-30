"""Select the active LLM provider from settings."""

from app.core.config import Settings, get_settings
from app.services.llm.base import LLMProvider
from app.services.llm.gemini import GeminiLLMProvider
from app.services.llm.openai import OpenAILLMProvider


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()

    if settings.llm_provider == "openai":
        return OpenAILLMProvider(
            api_key=settings.openai_api_key, model=settings.openai_chat_model
        )
    if settings.llm_provider == "gemini":
        return GeminiLLMProvider(
            api_key=settings.gemini_api_key, model=settings.gemini_chat_model
        )
    raise ValueError(f"Unknown llm_provider: {settings.llm_provider!r}")
