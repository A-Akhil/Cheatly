from __future__ import annotations

from typing import Any

from backend.llm.api_provider import GoogleGenAIProvider
from backend.llm.ollama_provider import OllamaProvider


class MockProvider:
	def generate(self, prompt: str) -> str:
		return (
			"- Acknowledge what they just said clearly.\n"
			"- Ask one follow-up question to keep the conversation moving.\n"
			"- Give a concise response grounded in the provided context."
		)


class ProviderManager:
	def __init__(self, config: dict[str, Any]) -> None:
		self._config = config
		self._provider = self._build_provider(config)

	def _build_provider(self, config: dict[str, Any]):
		provider_name = str(config.get("model_provider", {}).get("provider", "google")).lower()
		if provider_name == "mock":
			return MockProvider()

		if provider_name == "ollama":
			mp = config.get("model_provider", {})
			return OllamaProvider(
				host=mp.get("ollama_host", "http://127.0.0.1:11434"),
				model=mp.get("ollama_model", "llama3"),
				temperature=float(mp.get("temperature", 0.3)),
			)

		mp = config.get("model_provider", {})
		try:
			return GoogleGenAIProvider(
				model=mp.get("google_model", "gemma-3-1b-it"),
				fallback_model=mp.get("google_fallback_model", "gemini-3-flash-preview"),
			)
		except Exception:
			return MockProvider()

	def reload(self, config: dict[str, Any]) -> None:
		self._config = config
		self._provider = self._build_provider(config)

	def generate(self, prompt: str) -> str:
		return self._provider.generate(prompt)
