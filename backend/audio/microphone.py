from __future__ import annotations

import threading
from typing import Optional

from backend.audio.audio_buffer import AudioBuffer


class Microphone:
	def __init__(
		self,
		audio_buffer: AudioBuffer,
		sample_rate: int = 16000,
		channels: int = 1,
		chunk_duration_ms: int = 800,
		device_index: Optional[int] = None,
	) -> None:
		self._audio_buffer = audio_buffer
		self._sample_rate = sample_rate
		self._channels = channels
		self._chunk_duration_ms = chunk_duration_ms
		self._device_index = device_index

		self._running = False
		self._stream = None
		self._lock = threading.Lock()


	def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ANN001
		if status:
			return
		if not self._running:
			return
		# RawInputStream gives bytes-like data for int16 when dtype=int16.
		payload = bytes(indata)
		if payload:
			self._audio_buffer.push(payload)

	def start(self) -> None:
		with self._lock:
			if self._running:
				return

			try:
				import sounddevice as sd  # type: ignore
			except Exception as exc:
				raise RuntimeError("sounddevice is not installed") from exc

			blocksize = int(self._sample_rate * (self._chunk_duration_ms / 1000.0))
			self._stream = sd.RawInputStream(
				samplerate=self._sample_rate,
				channels=self._channels,
				dtype="int16",
				callback=self._callback,
				blocksize=blocksize,
				device=self._device_index,
			)
			self._stream.start()
			self._running = True

	def stop(self) -> None:
		with self._lock:
			self._running = False
			if self._stream is not None:
				self._stream.stop()
				self._stream.close()
				self._stream = None

	@property
	def is_running(self) -> bool:
		return self._running
