from __future__ import annotations

from collections import deque
from threading import Lock


class AudioBuffer:
	def __init__(self, max_chunks: int = 64) -> None:
		self._buffer = deque(maxlen=max_chunks)
		self._lock = Lock()

	def push(self, chunk: bytes) -> None:
		with self._lock:
			self._buffer.append(chunk)

	def pop_all(self) -> list[bytes]:
		with self._lock:
			data = list(self._buffer)
			self._buffer.clear()
		return data
