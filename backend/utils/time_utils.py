from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator


def now_ms() -> int:
	return int(time.time() * 1000)


@contextmanager
def stopwatch() -> Iterator[callable]:
	start = time.perf_counter()

	def elapsed_ms() -> float:
		return (time.perf_counter() - start) * 1000

	yield elapsed_ms
