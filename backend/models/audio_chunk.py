from __future__ import annotations

from dataclasses import dataclass, field
from time import time

import numpy as np


@dataclass
class AudioChunk:
    """Represents a chunk of audio data with source metadata."""

    data: np.ndarray
    source: str = "mic"  # "mic" or "meeting"
    timestamp_ms: int = field(default_factory=lambda: int(time() * 1000))
    sample_rate: int = 16000

    @property
    def duration_ms(self) -> float:
        """Duration of this chunk in milliseconds."""
        return (len(self.data) / self.sample_rate) * 1000
