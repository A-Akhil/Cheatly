from __future__ import annotations

from collections import deque
from threading import Lock


class TranscriptBuffer:
	def __init__(self, max_items: int = 128) -> None:
		self._items = deque(maxlen=max_items)
		self._lock = Lock()

	def append(self, text: str) -> None:
		cleaned = text.strip()
		if not cleaned:
			return
		with self._lock:
			self._items.append(cleaned)

	def get_all(self) -> list[str]:
		with self._lock:
			return list(self._items)
