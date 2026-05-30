"""LLM providers — provider-agnostic text generation.

    get_llm_provider()  — active provider from settings (Gemini/OpenAI)
    LLMProvider         — base class exposing generate(prompt, system)
"""

from app.services.llm.base import LLMProvider
from app.services.llm.factory import get_llm_provider

__all__ = ["LLMProvider", "get_llm_provider"]
