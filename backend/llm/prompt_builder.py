from __future__ import annotations

from typing import Iterable

from backend.context.knowledge_base import RetrievedChunk


class PromptBuilder:
	def build(self, transcript: str, history_text: str, rag_chunks: Iterable[RetrievedChunk]) -> str:
		context_block = "\n\n".join(
			[
				f"[Source: {chunk.source_name}]\n{chunk.chunk_text}"
				for chunk in rag_chunks
			]
		)

		return (
			"You are Cheatly, a live conversation assistant. "
			"Generate concise, practical bullet-point suggestions for the user to say next. "
			"If retrieved context is relevant, use it. If not relevant, ignore it.\n\n"
			"Output format rules:\n"
			"- 3 to 6 bullets\n"
			"- Each bullet one sentence\n"
			"- No markdown fences\n"
			"- No preamble or explanations\n\n"
			f"Recent conversation history:\n{history_text or '(none)'}\n\n"
			f"Current transcript:\n{transcript}\n\n"
			f"Retrieved reference context:\n{context_block or '(none)'}\n"
		)
