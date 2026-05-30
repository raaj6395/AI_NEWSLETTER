"""OpenAI chat provider — wired for a later switch from Gemini.

Lazy-imports `openai`; add it to requirements when switching `llm_provider`.
"""

import logging

from app.services.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAILLMProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str, temperature: float = 0.4):
        super().__init__(model=model)
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set")
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self.temperature = temperature

    def generate(self, prompt: str, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = self._client.chat.completions.create(
            model=self.model, messages=messages, temperature=self.temperature
        )
        return (resp.choices[0].message.content or "").strip()
