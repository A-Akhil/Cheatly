from __future__ import annotations

import os
from typing import Any

from backend.logging.logger import get_logger

logger = get_logger("backend.llm.litellm_provider")


class LiteLLMProvider:
    """Unified LLM provider using LiteLLM for wide model support."""

    def __init__(
        self,
        model: str,
        fallback_model: str | None = None,
        api_base: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> None:
        self.model = model
        self.fallback_model = fallback_model
        self.api_base = api_base
        self.temperature = temperature
        self.max_tokens = max_tokens

        try:
            import litellm
            self._litellm = litellm
            litellm.set_verbose = False
        except ImportError as exc:
            raise RuntimeError(
                "litellm package not installed. Run: pip install litellm"
            ) from exc

    def generate(self, prompt: str) -> str:
        """Generate completion using primary model, fallback on failure."""
        try:
            return self._call_model(self.model, prompt)
        except Exception as e:
            logger.warning(f"Primary model {self.model} failed: {e}")
            if self.fallback_model:
                logger.info(f"Trying fallback model: {self.fallback_model}")
                return self._call_model(self.fallback_model, prompt)
            raise

    def _call_model(self, model: str, prompt: str) -> str:
        """Call LiteLLM completion API."""
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if self.api_base:
            kwargs["api_base"] = self.api_base

        response = self._litellm.completion(**kwargs)
        content = response.choices[0].message.content
        return (content or "").strip()

    def generate_stream(self, prompt: str):
        """Stream completion for lower latency first-token."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True,
        }

        if self.api_base:
            kwargs["api_base"] = self.api_base

        for chunk in self._litellm.completion(**kwargs):
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content


class MockProvider:
    """Mock provider for testing without API calls."""

    def generate(self, prompt: str) -> str:
        return (
            "- Acknowledge what they just said clearly.\n"
            "- Ask one follow-up question to keep the conversation moving.\n"
            "- Give a concise response grounded in the provided context."
        )

    def generate_stream(self, prompt: str):
        for line in self.generate(prompt).split("\n"):
            yield line + "\n"
