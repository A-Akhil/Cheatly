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
			"You are an expert, quick-witted conversational wingman. "
			"Your goal is to provide the user with brilliant, context-aware suggestions on what to say next during their live conversation.\n\n"
			"CRITICAL OUTPUT RULES:\n"
			"- Output exactly 2 to 4 suggestions.\n"
			"- Make each suggestion short, punchy, and natural to speak out loud.\n"
			"- Do NOT use bullet points, dashes, asterisks, or markdown. Output plain text.\n"
			"- Put exactly ONE suggestion per line.\n"
			"- Do NOT include any preamble, explanations, or quotes. Just the exact words the user should say.\n\n"
			"If the retrieved context is highly relevant, use it to ground your suggestions. If not, ignore it.\n\n"
			f"Recent conversation history:\n{history_text or '(none)'}\n\n"
			f"Current transcript:\n{transcript}\n\n"
			f"Retrieved reference context:\n{context_block or '(none)'}\n"
		)
