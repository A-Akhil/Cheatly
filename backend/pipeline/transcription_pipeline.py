from __future__ import annotations

from backend.context.transcript_history import TranscriptHistory


class TranscriptionPipeline:
	def __init__(self, transcript_history: TranscriptHistory) -> None:
		self.transcript_history = transcript_history

	def ingest_text(self, text: str) -> None:
		self.transcript_history.append(text)
