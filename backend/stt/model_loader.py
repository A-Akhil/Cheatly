from __future__ import annotations


class ModelLoader:
	def __init__(self, model_size: str = "base") -> None:
		self.model_size = model_size

	def load_whisper(self) -> object | None:
		try:
			from faster_whisper import WhisperModel  # type: ignore
		except Exception:
			return None

		try:
			return WhisperModel(self.model_size, device="auto", compute_type="auto")
		except Exception:
			return None
