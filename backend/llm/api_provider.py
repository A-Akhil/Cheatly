from __future__ import annotations

import os


class GoogleGenAIProvider:
	def __init__(self, model: str, fallback_model: str | None = None) -> None:
		self.model = model
		self.fallback_model = fallback_model

		try:
			from google import genai  # type: ignore
		except Exception as exc:
			raise RuntimeError("google-genai package not installed") from exc

		self._client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

	def generate(self, prompt: str) -> str:
		try:
			response = self._client.models.generate_content(model=self.model, contents=prompt)
			return (response.text or "").strip()
		except Exception:
			if not self.fallback_model:
				raise
			response = self._client.models.generate_content(model=self.fallback_model, contents=prompt)
			return (response.text or "").strip()
