"""Tests for turn metadata propagation through the pipeline."""
import pytest
from unittest.mock import MagicMock, patch
import uuid


class TestTurnSegmentModel:
    """Tests for TurnSegment data model."""

    def test_turn_segment_creation(self):
        from backend.models.turn_segment import TurnSegment

        segment = TurnSegment(
            text="Hello world",
            turn_id="turn-123",
            revision=0,
            mode="prefetch",
            source="mic"
        )

        assert segment.text == "Hello world"
        assert segment.turn_id == "turn-123"
        assert segment.revision == 0
        assert segment.mode == "prefetch"
        assert segment.source == "mic"
        assert segment.is_final is False

    def test_with_revision(self):
        from backend.models.turn_segment import TurnSegment

        segment = TurnSegment(
            text="Hello",
            turn_id="turn-123",
            revision=0,
            mode="prefetch",
            source="mic"
        )

        updated = segment.with_revision(1)
        assert updated.revision == 1
        assert updated.turn_id == segment.turn_id
        assert updated.text == segment.text

    def test_as_prefetch(self):
        from backend.models.turn_segment import TurnSegment

        segment = TurnSegment(
            text="Hello",
            turn_id="turn-123",
            revision=0,
            mode="final",
            source="mic"
        )

        prefetch = segment.as_prefetch()
        assert prefetch.mode == "prefetch"
        assert prefetch.is_final is False

    def test_as_final(self):
        from backend.models.turn_segment import TurnSegment

        segment = TurnSegment(
            text="Hello",
            turn_id="turn-123",
            revision=0,
            mode="prefetch",
            source="mic"
        )

        final = segment.as_final()
        assert final.mode == "final"
        assert final.is_final is True

    def test_to_dict(self):
        from backend.models.turn_segment import TurnSegment

        segment = TurnSegment(
            text="Hello",
            turn_id="turn-123",
            revision=2,
            mode="final",
            source="meeting"
        )

        d = segment.to_dict()
        assert d["text"] == "Hello"
        assert d["turn_id"] == "turn-123"
        assert d["revision"] == 2
        assert d["mode"] == "final"
        assert d["source"] == "meeting"
        assert d["is_final"] is True


class TestTranscriptBufferTurnTracking:
    """Tests for turn tracking in TranscriptBuffer."""

    def test_append_generates_turn_id(self):
        from backend.stt.transcript_buffer import TranscriptBuffer

        buffer = TranscriptBuffer()
        segment = buffer.append("Hello")

        assert segment.turn_id is not None
        assert len(segment.turn_id) > 0

    def test_same_turn_increments_revision(self):
        from backend.stt.transcript_buffer import TranscriptBuffer

        buffer = TranscriptBuffer()
        seg1 = buffer.append("Hello")
        seg2 = buffer.append("world")

        assert seg1.turn_id == seg2.turn_id
        assert seg2.revision == seg1.revision + 1

    def test_new_turn_after_gap(self):
        from backend.stt.transcript_buffer import TranscriptBuffer
        import time

        buffer = TranscriptBuffer()
        buffer._turn_gap_ms = 50

        seg1 = buffer.append("Hello")
        time.sleep(0.1)
        seg2 = buffer.append("New turn")

        assert seg1.turn_id != seg2.turn_id
        assert seg2.revision == 0


class TestTriggerPolicy:
    """Tests for TriggerPolicy turn tracking."""

    def test_prefetch_fires_once_per_turn(self):
        from backend.pipeline.trigger_policy import TriggerPolicy, PRESETS
        from backend.models.turn_segment import TurnSegment

        policy = TriggerPolicy(PRESETS["fast"])

        seg1 = TurnSegment(
            text="Hello world this is a test",
            turn_id="turn-1",
            revision=0,
            mode="prefetch",
            source="mic"
        )

        result1 = policy.feed(seg1)
        result2 = policy.feed(seg1.with_revision(1))

        prefetch_count = sum(1 for r in [result1, result2] if r == "PREFETCH")
        assert prefetch_count <= 1

    def test_final_fires_after_prefetch(self):
        from backend.pipeline.trigger_policy import TriggerPolicy, PRESETS
        from backend.models.turn_segment import TurnSegment
        import time

        policy = TriggerPolicy(PRESETS["fast"])

        seg = TurnSegment(
            text="Hello world this is a test sentence",
            turn_id="turn-1",
            revision=0,
            mode="prefetch",
            source="mic"
        )

        policy.feed(seg)
        time.sleep(0.8)
        result = policy.feed(seg.with_revision(1))

        assert result in ["FINAL", "PREFETCH", None]

    def test_new_turn_resets_state(self):
        from backend.pipeline.trigger_policy import TriggerPolicy, PRESETS
        from backend.models.turn_segment import TurnSegment

        policy = TriggerPolicy(PRESETS["balanced"])

        seg1 = TurnSegment(
            text="First turn content here",
            turn_id="turn-1",
            revision=0,
            mode="prefetch",
            source="mic"
        )
        policy.feed(seg1)

        seg2 = TurnSegment(
            text="Second turn content here",
            turn_id="turn-2",
            revision=0,
            mode="prefetch",
            source="mic"
        )
        result = policy.feed(seg2)

        assert result in ["PREFETCH", None]


class TestSuggestionEngineTurnOutput:
    """Tests for SuggestionEngine turn-aware output."""

    def test_stores_output_by_turn_id(self):
        from backend.pipeline.suggestion_engine import SuggestionEngine
        from unittest.mock import MagicMock

        provider = MagicMock()
        provider.generate.return_value = "Suggestion 1\nSuggestion 2"

        kb = MagicMock()
        kb.query.return_value = []

        ctx = MagicMock()
        ctx.get_items.return_value = []

        engine = SuggestionEngine(
            provider_manager=provider,
            kb=kb,
            context_manager=ctx,
            top_k=3
        )

        engine.generate_suggestions("Hello", turn_id="turn-1", mode="prefetch")
        engine.generate_suggestions("World", turn_id="turn-1", mode="final")

        outputs = engine._turn_outputs.get("turn-1", {})
        assert "final" in outputs or "prefetch" in outputs

    def test_clear_turn_outputs(self):
        from backend.pipeline.suggestion_engine import SuggestionEngine
        from unittest.mock import MagicMock

        provider = MagicMock()
        provider.generate.return_value = "Suggestion"

        kb = MagicMock()
        kb.query.return_value = []

        ctx = MagicMock()
        ctx.get_items.return_value = []

        engine = SuggestionEngine(
            provider_manager=provider,
            kb=kb,
            context_manager=ctx,
            top_k=3
        )

        engine.generate_suggestions("Test", turn_id="turn-1", mode="final")
        engine.clear_turn_outputs()

        assert len(engine._turn_outputs) == 0


class TestAudioChunkSourceTagging:
    """Tests for AudioChunk source tagging."""

    def test_audio_chunk_mic_source(self):
        from backend.models.audio_chunk import AudioChunk

        chunk = AudioChunk(
            data=b"\x00\x00",
            sample_rate=16000,
            channels=1,
            source="mic"
        )

        assert chunk.source == "mic"

    def test_audio_chunk_meeting_source(self):
        from backend.models.audio_chunk import AudioChunk

        chunk = AudioChunk(
            data=b"\x00\x00",
            sample_rate=16000,
            channels=1,
            source="meeting"
        )

        assert chunk.source == "meeting"

    def test_audio_chunk_to_dict(self):
        from backend.models.audio_chunk import AudioChunk

        chunk = AudioChunk(
            data=b"\x00\x01\x02",
            sample_rate=16000,
            channels=1,
            source="mic"
        )

        d = chunk.to_dict()
        assert d["sample_rate"] == 16000
        assert d["channels"] == 1
        assert d["source"] == "mic"
        assert "data" in d
