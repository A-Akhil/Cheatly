from __future__ import annotations

import logging
from pathlib import Path


logger = logging.getLogger(__name__)


class ModelLoader:
	def __init__(
		self,
		model_size: str = "base",
		device: str = "cpu",
		compute_type: str = "int8",
		download_root: str | None = None,
		cpu_threads: int = 1,
		num_workers: int = 1,
	) -> None:
		self.model_size = model_size
		self.device = device
		self.compute_type = compute_type
		self.download_root = download_root
		self.cpu_threads = cpu_threads
		self.num_workers = num_workers

	def _resolve_local_snapshot(self, root_path: Path) -> str | None:
		repo_dir = root_path / f"models--Systran--faster-whisper-{self.model_size}"
		refs_main = repo_dir / "refs" / "main"
		if not refs_main.exists():
			return None

		try:
			revision = refs_main.read_text(encoding="utf-8", errors="ignore").strip()
		except Exception:
			return None

		if not revision:
			return None

		snap_dir = repo_dir / "snapshots" / revision
		required = ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]
		if snap_dir.is_dir() and all((snap_dir / f).exists() for f in required):
			return str(snap_dir)
		return None

	def load_whisper(self) -> object | None:
		logger.info(
			f"[stt] load_whisper: begin model_size={self.model_size} device={self.device} compute_type={self.compute_type}"
		)
		try:
			logger.info("[stt] load_whisper: importing faster_whisper.WhisperModel")
			from faster_whisper import WhisperModel  # type: ignore
		except Exception as exc:
			logger.warning(f"faster_whisper import failed: {exc}")
			return None

		try:
			logger.info("[stt] load_whisper: initializing WhisperModel (this may download model on first run)")
			download_root = None
			model_ref = self.model_size
			if self.download_root:
				root_path = Path(self.download_root)
				root_path.mkdir(parents=True, exist_ok=True)
				download_root = str(root_path)
				local_snapshot = self._resolve_local_snapshot(root_path)
				if local_snapshot:
					model_ref = local_snapshot
			return WhisperModel(
				model_ref,
				device=self.device,
				compute_type=self.compute_type,
				download_root=download_root,
				cpu_threads=self.cpu_threads,
				num_workers=self.num_workers,
			)
		except Exception as exc:
			logger.warning(
				f"Whisper model load failed (size={self.model_size}, device={self.device}, compute_type={self.compute_type}): {exc}"
			)
			return None
