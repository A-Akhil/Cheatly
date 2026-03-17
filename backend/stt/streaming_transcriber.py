from __future__ import annotations

import threading
import time
from typing import Callable

from backend.audio.audio_buffer import AudioBuffer
from backend.stt.transcript_buffer import TranscriptBuffer
from backend.stt.whisper_engine import WhisperEngine


class StreamingTranscriber:
	def __init__(
		self,
		audio_buffer: AudioBuffer,
		transcript_buffer: TranscriptBuffer,
		whisper: WhisperEngine,
		on_transcript: Callable[[str], None] | None = None,
	):
		self.audio_buffer = audio_buffer
		self.transcript_buffer = transcript_buffer
		self.whisper = whisper
		self.on_transcript = on_transcript
		self._running = False
		self._thread: threading.Thread | None = None

	def process_once(self) -> list[str]:
		outputs: list[str] = []
		for chunk in self.audio_buffer.pop_all():
			text = self.whisper.transcribe(chunk).strip()
			if text:
				self.transcript_buffer.append(text)
				if self.on_transcript is not None:
					self.on_transcript(text)
				outputs.append(text)
		return outputs

	def start(self) -> None:
		if self._running:
			return
		self._running = True
		self._thread = threading.Thread(target=self._loop, daemon=True, name="streaming-transcriber")
		self._thread.start()

	def stop(self) -> None:
		self._running = False

	def _loop(self) -> None:
		while self._running:
			self.process_once()
			time.sleep(0.05)

	@property
	def is_running(self) -> bool:
		return self._running
