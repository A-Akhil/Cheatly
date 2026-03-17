from __future__ import annotations

from collections import deque


class ConversationContextManager:
	def __init__(self, max_items: int = 20) -> None:
		self._max_items = max_items
		self._items: deque[str] = deque(maxlen=max_items)

	def add_transcript(self, text: str) -> None:
		cleaned = text.strip()
		if cleaned:
			self._items.append(cleaned)

	def get_history_text(self) -> str:
		return "\n".join(self._items)

	def clear(self) -> None:
		self._items.clear()
