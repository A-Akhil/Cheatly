from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from time import time


@dataclass
class SessionState:
	session_id: str
	started_at: float
	status: str


class SessionManager:
	def __init__(self) -> None:
		self._lock = threading.Lock()
		self._state = self._new_session_state()

	def _new_session_state(self) -> SessionState:
		return SessionState(session_id=str(uuid.uuid4()), started_at=time(), status="active")

	def reset(self) -> SessionState:
		with self._lock:
			self._state = self._new_session_state()
			return self._state

	def get(self) -> SessionState:
		with self._lock:
			return self._state
