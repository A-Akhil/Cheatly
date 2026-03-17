from __future__ import annotations

from backend.audio.audio_buffer import AudioBuffer
from backend.audio.microphone import Microphone


class StreamManager:
	def __init__(self, microphone: Microphone, audio_buffer: AudioBuffer) -> None:
		self.microphone = microphone
		self.audio_buffer = audio_buffer
		self._running = False

	def start(self) -> None:
		if self._running:
			return
		self.microphone.start()
		self._running = True

	def stop(self) -> None:
		if not self._running:
			return
		self.microphone.stop()
		self._running = False

	@property
	def is_running(self) -> bool:
		return self._running
