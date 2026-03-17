from __future__ import annotations


class ResponseParser:
	def to_bullets(self, text: str) -> list[str]:
		lines = [line.strip() for line in text.splitlines() if line.strip()]
		bullets: list[str] = []

		for line in lines:
			normalized = line
			for prefix in ("- ", "* ", "• "):
				if normalized.startswith(prefix):
					normalized = normalized[len(prefix):].strip()
			if normalized and normalized not in bullets:
				bullets.append(normalized)

		if not bullets and text.strip():
			bullets = [text.strip()]

		return bullets[:6]
