from __future__ import annotations

from backend.context.knowledge_base import KnowledgeBase
from backend.llm.prompt_builder import PromptBuilder
from backend.llm.provider_manager import ProviderManager
from backend.llm.response_parser import ResponseParser
from backend.pipeline.context_manager import ConversationContextManager


class SuggestionEngine:
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

	def generate_suggestions(self, transcript: str) -> dict:
		self.context_manager.add_transcript(transcript)
		history = self.context_manager.get_history_text()
		chunks = self.kb.search(transcript, top_k=self.top_k)

		prompt = self.prompt_builder.build(
			transcript=transcript,
			history_text=history,
			rag_chunks=chunks,
		)
		raw = self.provider_manager.generate(prompt)
		bullets = self.response_parser.to_bullets(raw)

		return {
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
