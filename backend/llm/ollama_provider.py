from __future__ import annotations

import requests


class OllamaProvider:
	def __init__(self, host: str, model: str, temperature: float = 0.3) -> None:
		self.host = host.rstrip("/")
		self.model = model
		self.temperature = temperature

	def generate(self, prompt: str) -> str:
		response = requests.post(
			f"{self.host}/api/generate",
			json={
				"model": self.model,
				"prompt": prompt,
				"stream": False,
				"options": {"temperature": self.temperature},
			},
			timeout=120,
		)
		response.raise_for_status()
		data = response.json()
		return str(data.get("response", "")).strip()
