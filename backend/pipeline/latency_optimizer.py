from __future__ import annotations


class LatencyOptimizer:
	def __init__(self, debounce_ms: int = 200) -> None:
		self.debounce_ms = debounce_ms
