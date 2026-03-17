from __future__ import annotations

import threading
from typing import Callable


class ManagedThread:
	def __init__(self, target: Callable[[], None], name: str) -> None:
		self._target = target
		self._thread = threading.Thread(target=self._target, daemon=True, name=name)

	def start(self) -> None:
		if not self._thread.is_alive():
			self._thread.start()

	def is_alive(self) -> bool:
		return self._thread.is_alive()
