"""Gemini chat/text provider (Google AI Studio free tier)."""

import logging

from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class GeminiLLMProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str, temperature: float = 0.4):
        super().__init__(model=model)
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        from google import genai

        self._genai = genai
        self._client = genai.Client(api_key=api_key)
        self.temperature = temperature

    def generate(self, prompt: str, system: str | None = None) -> str:
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=self.temperature,
            system_instruction=system,
        )
        resp = self._client.models.generate_content(
            model=self.model, contents=prompt, config=config
        )
        return (resp.text or "").strip()
