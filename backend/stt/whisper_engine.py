from __future__ import annotations

import numpy as np


class WhisperEngine:
	def __init__(self, model: object | None, sample_rate: int = 16000) -> None:
		self._model = model
		self._sample_rate = sample_rate


	def transcribe(self, audio_chunk: bytes) -> str:
		if self._model is None or not audio_chunk:
			return ""

		try:
			pcm = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
			segments, _ = self._model.transcribe(pcm, language="en", vad_filter=True)
			return " ".join(seg.text.strip() for seg in segments if seg.text and seg.text.strip()).strip()
		except Exception:
			return ""
