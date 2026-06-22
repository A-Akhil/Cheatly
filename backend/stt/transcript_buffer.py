from __future__ import annotations

import uuid
from collections import deque
from threading import Lock
from time import time

from backend.models.turn_segment import TurnSegment


class TranscriptBuffer:
    """Buffer for transcript segments with turn tracking."""

    TURN_GAP_MS = 1200  # Gap threshold for new turn detection

    def __init__(self, max_items: int = 128) -> None:
        self._segments: deque[TurnSegment] = deque(maxlen=max_items)
        self._lock = Lock()
        self._current_turn_id: str | None = None
        self._current_revision: int = 0
        self._last_timestamp_ms: int = 0

    def append(self, text: str, source: str = "mic") -> TurnSegment | None:
        """Append text and return the created TurnSegment."""
        cleaned = text.strip()
        if not cleaned:
            return None

        now_ms = int(time() * 1000)

        with self._lock:
            is_new_turn = self._should_start_new_turn(now_ms)

            if is_new_turn:
                self._current_turn_id = str(uuid.uuid4())
                self._current_revision = 0
            else:
                self._current_revision += 1

            segment = TurnSegment(
                text=cleaned,
                turn_id=self._current_turn_id or str(uuid.uuid4()),
                revision=self._current_revision,
                mode="prefetch",
                source=source,
                timestamp_ms=now_ms,
                is_final=False,
            )

            self._segments.append(segment)
            self._last_timestamp_ms = now_ms

            return segment

    def _should_start_new_turn(self, now_ms: int) -> bool:
        """Determine if we should start a new turn based on time gap."""
        if self._current_turn_id is None:
            return True
        if self._last_timestamp_ms == 0:
            return True
        gap = now_ms - self._last_timestamp_ms
        return gap > self.TURN_GAP_MS

    def mark_final(self, turn_id: str) -> None:
        """Mark all segments for a turn as final."""
        with self._lock:
            for seg in self._segments:
                if seg.turn_id == turn_id:
                    seg.is_final = True
                    seg.mode = "final"

    def get_current_turn(self) -> list[TurnSegment]:
        """Get all segments for the current turn."""
        with self._lock:
            if not self._current_turn_id:
                return []
            return [s for s in self._segments if s.turn_id == self._current_turn_id]

    def get_current_turn_text(self) -> str:
        """Get concatenated text for current turn."""
        segments = self.get_current_turn()
        return " ".join(s.text for s in segments)

    def get_all(self) -> list[str]:
        """Get all segment texts (backward compatible)."""
        with self._lock:
            return [s.text for s in self._segments]

    def get_all_segments(self) -> list[TurnSegment]:
        """Get all segments."""
        with self._lock:
            return list(self._segments)

    def get_latest_segment(self) -> TurnSegment | None:
        """Get the most recent segment."""
        with self._lock:
            return self._segments[-1] if self._segments else None

    def clear(self) -> None:
        """Clear all segments and reset turn tracking."""
        with self._lock:
            self._segments.clear()
            self._current_turn_id = None
            self._current_revision = 0
            self._last_timestamp_ms = 0
