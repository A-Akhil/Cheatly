from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import time
from typing import Any

from backend.models.turn_segment import TurnSegment


class TriggerEvent(Enum):
    PREFETCH = "prefetch"
    FINAL = "final"


@dataclass
class TriggerPreset:
    """Configuration for trigger timing."""
    stability_window_ms: int
    final_silence_ms: int
    min_prefetch_interval_ms: int
    extra_prefetch_delta_tokens: int

    @classmethod
    def from_config(cls, config: dict[str, Any], preset_name: str) -> "TriggerPreset":
        """Load preset from config."""
        presets = config.get("trigger", {}).get("presets", {})
        preset = presets.get(preset_name, presets.get("balanced", {}))

        return cls(
            stability_window_ms=preset.get("stability_window_ms", 500),
            final_silence_ms=preset.get("final_silence_ms", 950),
            min_prefetch_interval_ms=preset.get("min_prefetch_interval_ms", 800),
            extra_prefetch_delta_tokens=preset.get("extra_prefetch_delta_tokens", 0),
        )


FILLER_WORDS = {"um", "uh", "er", "ah", "like", "you know", "hmm", "hm"}
CONTINUATION_CUES = {"and", "but", "so", "because", "however", "although", "or"}
MIN_TOKENS_FOR_PREFETCH = 8


PRESETS: dict[str, TriggerPreset] = {
    "fast": TriggerPreset(
        stability_window_ms=350,
        final_silence_ms=700,
        min_prefetch_interval_ms=600,
        extra_prefetch_delta_tokens=6,
    ),
    "balanced": TriggerPreset(
        stability_window_ms=500,
        final_silence_ms=950,
        min_prefetch_interval_ms=800,
        extra_prefetch_delta_tokens=0,
    ),
    "accurate": TriggerPreset(
        stability_window_ms=700,
        final_silence_ms=1250,
        min_prefetch_interval_ms=1000,
        extra_prefetch_delta_tokens=0,
    ),
}


class TriggerPolicy:
    """
    Two-stage trigger policy for LLM generation.

    Stage A (prefetch): Fire early while speaker is talking for low-latency draft.
    Stage B (final): Fire on turn completion for committed response.
    """

    def __init__(self, preset: TriggerPreset, preset_name: str = "balanced") -> None:
        self.preset = preset
        self.preset_name = preset_name

        self._last_prefetch_time_ms: int = 0
        self._prefetch_fired_for_turn: set[str] = set()
        self._last_segment_time_ms: int = 0
        self._accumulated_text: str = ""
        self._current_turn_id: str | None = None

    def reload(self, preset_name: str) -> None:
        """Reload with a different preset."""
        self.preset = PRESETS.get(preset_name, PRESETS["balanced"])
        self.preset_name = preset_name

    def feed(self, segment: TurnSegment) -> TriggerEvent | None:
        """
        Process a segment and determine if we should trigger.
        Returns PREFETCH, FINAL, or None.
        """
        now_ms = int(time() * 1000)

        if segment.turn_id != self._current_turn_id:
            self._start_new_turn(segment)

        self._accumulated_text = segment.text
        is_first_segment = self._last_segment_time_ms == 0
        time_since_last = now_ms - self._last_segment_time_ms if not is_first_segment else 0
        self._last_segment_time_ms = now_ms

        if self._should_trigger_final(time_since_last, segment):
            self._prefetch_fired_for_turn.discard(segment.turn_id)
            return TriggerEvent.FINAL

        if self._should_trigger_prefetch(now_ms, segment):
            self._last_prefetch_time_ms = now_ms
            self._prefetch_fired_for_turn.add(segment.turn_id)
            return TriggerEvent.PREFETCH

        return None

    def check_silence(self, last_segment_time_ms: int) -> TriggerEvent | None:
        """Check if silence duration warrants a final trigger."""
        now_ms = int(time() * 1000)
        silence_duration = now_ms - last_segment_time_ms

        if silence_duration >= self.preset.final_silence_ms:
            if self._current_turn_id and self._accumulated_text.strip():
                if not self._has_continuation_cue():
                    return TriggerEvent.FINAL
                if silence_duration >= self.preset.final_silence_ms + self._grace_extension_ms():
                    return TriggerEvent.FINAL

        return None

    def _start_new_turn(self, segment: TurnSegment) -> None:
        """Reset state for a new turn."""
        self._current_turn_id = segment.turn_id
        self._accumulated_text = ""
        self._prefetch_fired_for_turn.discard(segment.turn_id)

    def _should_trigger_prefetch(self, now_ms: int, segment: TurnSegment) -> bool:
        """Determine if we should fire a prefetch."""
        if segment.token_count < MIN_TOKENS_FOR_PREFETCH:
            return False

        if self._is_filler_only(segment.text):
            return False

        if segment.turn_id in self._prefetch_fired_for_turn:
            if self.preset.extra_prefetch_delta_tokens == 0:
                return False

        time_since_last_prefetch = now_ms - self._last_prefetch_time_ms
        if time_since_last_prefetch < self.preset.min_prefetch_interval_ms:
            return False

        return True

    def _should_trigger_final(self, time_since_last_ms: int, segment: TurnSegment) -> bool:
        """Determine if we should fire a final trigger."""
        if segment.is_final:
            return True

        if time_since_last_ms >= self.preset.final_silence_ms:
            if not self._has_continuation_cue():
                return True

        return False

    def _is_filler_only(self, text: str) -> bool:
        """Check if text is only filler words."""
        words = set(text.lower().split())
        return words.issubset(FILLER_WORDS)

    def _has_continuation_cue(self) -> bool:
        """Check if text ends with a continuation cue."""
        words = self._accumulated_text.lower().split()
        if not words:
            return False
        return words[-1] in CONTINUATION_CUES

    def _grace_extension_ms(self) -> int:
        """Get grace extension for long-question pauses."""
        if self.preset_name == "fast":
            return 300
        return 500

    def reset(self) -> None:
        """Reset all state."""
        self._last_prefetch_time_ms = 0
        self._prefetch_fired_for_turn.clear()
        self._last_segment_time_ms = 0
        self._accumulated_text = ""
        self._current_turn_id = None
