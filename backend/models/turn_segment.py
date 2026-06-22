from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from time import time


@dataclass
class TurnSegment:
    """Represents a segment of transcribed speech within a conversation turn."""

    text: str
    turn_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    revision: int = 0
    mode: str = "final"  # "prefetch" or "final"
    source: str = "mic"  # "mic" or "meeting"
    timestamp_ms: int = field(default_factory=lambda: int(time() * 1000))
    is_final: bool = False
    token_count: int = 0

    def __post_init__(self) -> None:
        if self.token_count == 0:
            self.token_count = len(self.text.split())

    def with_revision(self, new_text: str) -> TurnSegment:
        """Create a new segment with incremented revision and updated text."""
        return TurnSegment(
            text=new_text,
            turn_id=self.turn_id,
            revision=self.revision + 1,
            mode=self.mode,
            source=self.source,
            timestamp_ms=int(time() * 1000),
            is_final=self.is_final,
        )

    def as_prefetch(self) -> TurnSegment:
        """Return a copy marked as prefetch mode."""
        return TurnSegment(
            text=self.text,
            turn_id=self.turn_id,
            revision=self.revision,
            mode="prefetch",
            source=self.source,
            timestamp_ms=self.timestamp_ms,
            is_final=False,
            token_count=self.token_count,
        )

    def as_final(self) -> TurnSegment:
        """Return a copy marked as final mode."""
        return TurnSegment(
            text=self.text,
            turn_id=self.turn_id,
            revision=self.revision,
            mode="final",
            source=self.source,
            timestamp_ms=self.timestamp_ms,
            is_final=True,
            token_count=self.token_count,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "turn_id": self.turn_id,
            "revision": self.revision,
            "mode": self.mode,
            "source": self.source,
            "text": self.text,
            "timestamp_ms": self.timestamp_ms,
            "is_final": self.is_final,
            "token_count": self.token_count,
        }
