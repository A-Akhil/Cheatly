from __future__ import annotations

from typing import Any

from backend.llm.litellm_provider import LiteLLMProvider, MockProvider
from backend.logging.logger import get_logger

logger = get_logger("backend.llm.provider_manager")


class ProviderManager:
    """Manages LLM provider lifecycle and configuration."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._provider = self._build_provider(config)

    def _build_provider(self, config: dict[str, Any]):
        mp = config.get("model_provider", {})
        provider_type = str(mp.get("provider", "litellm")).lower()

        if provider_type == "mock":
            logger.info("Using mock provider")
            return MockProvider()

        if provider_type == "ollama":
            model = mp.get("model", "ollama/llama3.2:3b")
            fallback_model = mp.get("fallback_model")
            api_base = mp.get("api_base", "http://127.0.0.1:11434")
            temperature = float(mp.get("temperature", 0.3))
            max_tokens = int(mp.get("max_tokens", 1024))

            logger.info(f"Using Ollama via LiteLLM with model={model}, api_base={api_base}, fallback={fallback_model}")

            try:
                return LiteLLMProvider(
                    model=model,
                    fallback_model=fallback_model,
                    api_base=api_base,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as e:
                logger.error(f"Failed to initialize Ollama provider: {e}, falling back to mock")
                return MockProvider()

        if provider_type not in {"litellm", "google", "openai", "anthropic", "gemini"}:
            logger.warning(f"Unknown provider '{provider_type}', defaulting to LiteLLM")

        model = mp.get("model", "gpt-4")
        fallback_model = mp.get("fallback_model")
        api_base = mp.get("api_base")
        temperature = float(mp.get("temperature", 0.3))
        max_tokens = int(mp.get("max_tokens", 1024))

        logger.info(f"Using LiteLLM with model={model}, fallback={fallback_model}")

        try:
            return LiteLLMProvider(
                model=model,
                fallback_model=fallback_model,
                api_base=api_base,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            logger.error(f"Failed to initialize LiteLLM: {e}, falling back to mock")
            return MockProvider()

    def reload(self, config: dict[str, Any]) -> None:
        self._config = config
        self._provider = self._build_provider(config)

    def generate(self, prompt: str) -> str:
        return self._provider.generate(prompt)

    def generate_stream(self, prompt: str):
        if hasattr(self._provider, "generate_stream"):
            yield from self._provider.generate_stream(prompt)
        else:
            yield self._provider.generate(prompt)
