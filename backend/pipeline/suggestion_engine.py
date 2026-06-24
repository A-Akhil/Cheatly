from __future__ import annotations

from typing import Any

from backend.context.knowledge_base import KnowledgeBase
from backend.llm.prompt_builder import PromptBuilder
from backend.llm.provider_manager import ProviderManager
from backend.llm.response_parser import ResponseParser
from backend.models.turn_segment import TurnSegment
from backend.pipeline.context_manager import ConversationContextManager


class SuggestionEngine:
    """Generates suggestions from transcript segments."""

    def __init__(
        self,
        provider_manager: ProviderManager,
        kb: KnowledgeBase,
        context_manager: ConversationContextManager,
        top_k: int = 5,
    ) -> None:
        self.provider_manager = provider_manager
        self.kb = kb
        self.context_manager = context_manager
        self.prompt_builder = PromptBuilder()
        self.response_parser = ResponseParser()
        self.top_k = top_k
        self._turn_outputs: dict[str, dict[str, Any]] = {}

    def generate_suggestions(self, transcript: str, mode: str = "final", turn_id: str | None = None, revision: int = 0) -> dict:
        """Generate suggestions for transcript text."""
        self.context_manager.add_transcript(transcript)
        history = self.context_manager.get_history_text()
        chunks = self.kb.search(transcript, top_k=self.top_k)

        prompt = self.prompt_builder.build(
            transcript=transcript,
            history_text=history,
            rag_chunks=chunks,
        )
        try:
            raw = self.provider_manager.generate(prompt)
            bullets = self.response_parser.to_bullets(raw)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"LLM generation failed: {e}")
            raw = ""
            bullets = [f"⚠️ LLM Error: {e}"]

        result = {
            "turn_id": turn_id,
            "revision": revision,
            "mode": mode,
            "transcript": transcript,
            "suggestions": bullets,
            "retrieved": [
                {
                    "document_id": c.document_id,
                    "source_name": c.source_name,
                    "score": c.score,
                }
                for c in chunks
            ],
            "raw": raw,
        }

        if turn_id:
            self._store_turn_output(turn_id, mode, result)

        return result

    def generate_from_segment(self, segment: TurnSegment) -> dict:
        """Generate suggestions from a TurnSegment."""
        return self.generate_suggestions(
            transcript=segment.text,
            mode=segment.mode,
            turn_id=segment.turn_id,
            revision=segment.revision,
        )

    def _store_turn_output(self, turn_id: str, mode: str, result: dict) -> None:
        """Store output per turn. Final supersedes prefetch."""
        existing = self._turn_outputs.get(turn_id)

        if existing is None or mode == "final" or existing.get("mode") != "final":
            self._turn_outputs[turn_id] = result

    def get_turn_output(self, turn_id: str) -> dict | None:
        """Get latest output for a turn."""
        return self._turn_outputs.get(turn_id)

    def clear_turn_outputs(self) -> None:
        """Clear all stored turn outputs."""
        self._turn_outputs.clear()
