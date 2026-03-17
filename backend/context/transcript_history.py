from __future__ import annotations

import threading
from dataclasses import dataclass
from time import time


@dataclass
class TranscriptSegment:
	text: str
	timestamp: float


class TranscriptHistory:
	def __init__(self) -> None:
		self._segments: list[TranscriptSegment] = []
		self._lock = threading.Lock()

	def append(self, text: str) -> TranscriptSegment:
		segment = TranscriptSegment(text=text, timestamp=time())
		with self._lock:
			self._segments.append(segment)
		return segment

	def get_all(self) -> list[TranscriptSegment]:
		with self._lock:
			return list(self._segments)

	def get_last_n_text(self, n: int = 8) -> str:
		with self._lock:
			return "\n".join(seg.text for seg in self._segments[-n:])

	def clear(self) -> None:
		with self._lock:
			self._segments.clear()
