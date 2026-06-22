from __future__ import annotations

import threading
import time
from typing import Callable
import logging

from backend.audio.audio_buffer import AudioBuffer
from backend.stt.transcript_buffer import TranscriptBuffer
from backend.stt.whisper_engine import WhisperEngine


logger = logging.getLogger(__name__)


class StreamingTranscriber:
	def __init__(
		self,
		audio_buffer: AudioBuffer,
		transcript_buffer: TranscriptBuffer,
		whisper: WhisperEngine,
		on_transcript: Callable[[str], None] | None = None,
		on_segment=None,
	):
		self.audio_buffer = audio_buffer
		self.transcript_buffer = transcript_buffer
		self.whisper = whisper
		self.on_transcript = on_transcript
		self.on_segment = on_segment  # Called with TurnSegment after each transcription
		self._running = False
		self._thread: threading.Thread | None = None

	def process_once(self) -> list[str]:
		outputs: list[str] = []
		try:
			chunks = self.audio_buffer.pop_all()
		except Exception:
			logger.exception("[stt] process_once: failed to pop audio chunks")
			return outputs

		for chunk in chunks:
			try:
				text = self.whisper.transcribe(chunk).strip()
			except Exception:
				logger.exception(f"[stt] process_once: transcribe failed chunk_bytes={len(chunk)}")
				continue

			if text:
				segment = self.transcript_buffer.append(text)
				if self.on_transcript is not None:
					self.on_transcript(text)
				if self.on_segment is not None and segment is not None:
					self.on_segment(segment)
				outputs.append(text)
		return outputs

	def start(self) -> None:
		if self._running:
			return
		logger.info("[stt] streaming_transcriber.start")
		self._running = True
		self._thread = threading.Thread(target=self._loop, daemon=True, name="streaming-transcriber")
		self._thread.start()

	def stop(self) -> None:
		logger.info("[stt] streaming_transcriber.stop")
		self._running = False

	def _loop(self) -> None:
		logger.info("[stt] streaming_transcriber.loop begin")
		while self._running:
			try:
				self.process_once()
			except Exception:
				logger.exception("[stt] streaming_transcriber.loop iteration failed")
			time.sleep(0.05)
		logger.info("[stt] streaming_transcriber.loop end")

	@property
	def is_running(self) -> bool:
		return self._running
