"""LLM provider abstraction for text generation.

Concrete providers (Gemini now, OpenAI later) implement `generate()`. Selected
by the `llm_provider` setting via `factory.get_llm_provider()`.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    #: Stable identifier ("gemini" | "openai").
    name: str = "base"

    def __init__(self, model: str):
        self.model = model

    @abstractmethod
    def generate(self, prompt: str, system: str | None = None) -> str:
        """Return the model's text completion for a prompt (+ optional system)."""
        raise NotImplementedError
