from __future__ import annotations

import numpy as np
from typing import Callable
import logging
import multiprocessing as mp
import queue
import time

from backend.stt.whisper_worker import run_whisper_worker


logger = logging.getLogger(__name__)


class WhisperEngine:
	def __init__(
		self,
		model: object | None,
		sample_rate: int = 16000,
		model_factory: Callable[[], object | None] | None = None,
		worker_config: dict | None = None,
		isolate_process: bool = False,
		worker_timeout_sec: float = 15.0,
	) -> None:
		self._model = model
		self._sample_rate = sample_rate
		self._model_factory = model_factory
		self._load_attempted = model is not None
		self._isolate_process = isolate_process
		self._worker_config = worker_config or {}
		self._worker_timeout_sec = worker_timeout_sec

		self._task_queue: mp.Queue | None = None
		self._result_queue: mp.Queue | None = None
		self._worker_process: mp.Process | None = None
		self._job_id = 0
		self._next_worker_retry_ts = 0.0
		self._worker_retry_backoff_sec = 5.0
		self._worker_ready = False
		self._worker_consecutive_failures = 0
		self._worker_max_failures = 3
		self._worker_disabled = False
		self._worker_candidates = self._build_worker_candidates(self._worker_config)
		self._worker_candidate_index = 0
		if self._worker_candidates:
			self._worker_max_failures = max(self._worker_max_failures, len(self._worker_candidates) * 2)

	def _build_worker_candidates(self, base_cfg: dict) -> list[dict]:
		model_size = str(base_cfg.get("model_size", "base"))
		compute_type = str(base_cfg.get("compute_type", "float32"))

		model_sizes: list[str] = [model_size]
		for m in base_cfg.get("fallback_model_sizes", []):
			ms = str(m).strip()
			if ms and ms not in model_sizes:
				model_sizes.append(ms)

		compute_types: list[str] = [compute_type]
		for ct in base_cfg.get("fallback_compute_types", []):
			cts = str(ct).strip()
			if cts and cts not in compute_types:
				compute_types.append(cts)

		candidates: list[dict] = []
		for ms in model_sizes:
			for ct in compute_types:
				cfg = dict(base_cfg)
				cfg["model_size"] = ms
				cfg["compute_type"] = ct
				candidates.append(cfg)
		return candidates or [dict(base_cfg)]

	def _current_worker_config(self) -> dict:
		if not self._worker_candidates:
			return dict(self._worker_config)
		idx = max(0, min(self._worker_candidate_index, len(self._worker_candidates) - 1))
		return dict(self._worker_candidates[idx])

	def _rotate_worker_candidate(self) -> None:
		if not self._worker_candidates:
			return
		if self._worker_candidate_index < len(self._worker_candidates) - 1:
			self._worker_candidate_index += 1
			cfg = self._worker_candidates[self._worker_candidate_index]
			logger.warning(
				"[stt] whisper worker trying fallback candidate "
				f"model={cfg.get('model_size')} compute_type={cfg.get('compute_type')}"
			)

	def _ensure_model_loaded(self) -> None:
		if self._isolate_process:
			self._ensure_worker_ready()
			return

		if self._model is not None or self._load_attempted:
			return
		self._load_attempted = True
		if self._model_factory is None:
			return
		try:
			self._model = self._model_factory()
		except Exception:
			self._model = None

	def _ensure_worker_ready(self, force: bool = False) -> None:
		if self._worker_disabled:
			return

		if self._worker_process is not None and self._worker_process.is_alive():
			if self._worker_ready:
				return

			self._poll_existing_worker_ready(force=force)
			return

		now = time.time()
		if not force and now < self._next_worker_retry_ts:
			return

		worker_cfg = self._current_worker_config()
		logger.info(
			"[stt] whisper worker: starting isolated process "
			f"model={worker_cfg.get('model_size')} compute_type={worker_cfg.get('compute_type')}"
		)
		ctx = mp.get_context("spawn")
		self._task_queue = ctx.Queue()
		self._result_queue = ctx.Queue()
		self._worker_process = ctx.Process(
			target=run_whisper_worker,
			args=(self._task_queue, self._result_queue, worker_cfg),
			daemon=True,
			name="whisper-worker",
		)
		self._worker_process.start()
		self._worker_ready = False

		if force:
			self._poll_existing_worker_ready(force=True)
			return

		try:
			msg = self._result_queue.get(timeout=self._worker_timeout_sec)
		except queue.Empty:
			logger.error("[stt] whisper worker: no readiness response received")
			self._record_worker_failure()
			return

		if msg.get("type") == "ready":
			logger.info("[stt] whisper worker: ready")
			self._worker_ready = True
			self._worker_consecutive_failures = 0
			self._next_worker_retry_ts = 0.0
			return

		if msg.get("type") == "init_error":
			logger.error(f"[stt] whisper worker init failed: {msg.get('error', 'unknown')}")
			self._terminate_worker()
			self._record_worker_failure()
			return

		logger.error(f"[stt] whisper worker: unexpected init message {msg}")
		self._record_worker_failure()

	def _poll_existing_worker_ready(self, force: bool) -> None:
		if self._result_queue is None:
			return

		if not force:
			try:
				msg = self._result_queue.get(timeout=0.1)
			except queue.Empty:
				return

			self._handle_worker_init_message(msg)
			return

		# Dynamic wait for startup preload: no hard timeout, wait until worker reports ready/failure.
		wait_started = time.time()
		last_log = wait_started
		while True:
			if self._worker_process is None or not self._worker_process.is_alive():
				logger.error("[stt] whisper worker exited before signaling readiness")
				self._terminate_worker()
				self._record_worker_failure()
				return

			try:
				msg = self._result_queue.get(timeout=1.0)
			except queue.Empty:
				now = time.time()
				if now - last_log >= 15:
					elapsed = int(now - wait_started)
					logger.info(f"[stt] whisper worker preload still in progress ({elapsed}s)")
					last_log = now
				continue

			if self._handle_worker_init_message(msg):
				return

	def _handle_worker_init_message(self, msg: object) -> bool:
		if not isinstance(msg, dict):
			return False

		if msg.get("type") == "ready":
			logger.info("[stt] whisper worker: ready")
			self._worker_ready = True
			self._worker_consecutive_failures = 0
			self._next_worker_retry_ts = 0.0
			return True

		if msg.get("type") == "init_error":
			logger.error(f"[stt] whisper worker init failed: {msg.get('error', 'unknown')}")
			self._terminate_worker()
			self._record_worker_failure()
			return True

		logger.error(f"[stt] whisper worker: unexpected init message {msg}")
		return False

	def _record_worker_failure(self) -> None:
		self._worker_consecutive_failures += 1
		self._rotate_worker_candidate()
		if self._worker_consecutive_failures >= self._worker_max_failures:
			if not self._worker_disabled:
				logger.error(
					f"[stt] whisper worker disabled after {self._worker_consecutive_failures} consecutive failures"
				)
			self._worker_disabled = True
			self._next_worker_retry_ts = float("inf")
			return

		self._next_worker_retry_ts = time.time() + self._worker_retry_backoff_sec

	def _terminate_worker(self) -> None:
		if self._worker_process is not None:
			if self._worker_process.is_alive():
				self._worker_process.terminate()
			self._worker_process.join(timeout=1.0)
		self._worker_process = None
		self._task_queue = None
		self._result_queue = None
		self._worker_ready = False


	def transcribe(self, audio_chunk: bytes) -> str:
		if self._isolate_process:
			return self._transcribe_in_worker(audio_chunk)

		self._ensure_model_loaded()
		if self._model is None or not audio_chunk:
			return ""

		try:
			pcm = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
			segments, _ = self._model.transcribe(pcm, language="en", vad_filter=True)
			return " ".join(seg.text.strip() for seg in segments if seg.text and seg.text.strip()).strip()
		except Exception:
			return ""

	def _transcribe_in_worker(self, audio_chunk: bytes) -> str:
		if not audio_chunk:
			return ""

		if self._worker_disabled:
			return ""

		self._ensure_worker_ready()
		if self._worker_process is None or not self._worker_process.is_alive() or self._task_queue is None or self._result_queue is None:
			logger.error("[stt] whisper worker unavailable after startup")
			return ""

		self._job_id += 1
		job_id = self._job_id

		try:
			self._task_queue.put({"job_id": job_id, "audio_chunk": audio_chunk})
		except Exception:
			logger.exception("[stt] failed to enqueue audio chunk for whisper worker")
			return ""

		try:
			while True:
				msg = self._result_queue.get(timeout=self._worker_timeout_sec)
				if msg.get("type") != "result":
					continue
				if int(msg.get("job_id", -1)) != job_id:
					continue
				if msg.get("error"):
					logger.warning(f"[stt] whisper worker transcribe error: {msg.get('error')}")
				return str(msg.get("text", ""))
		except queue.Empty:
			logger.error("[stt] whisper worker timed out while waiting for transcription result")
			if self._worker_process is not None and not self._worker_process.is_alive():
				logger.error("[stt] whisper worker died during transcription")
				self._terminate_worker()
			return ""

	def preload(self) -> bool:
		if self._isolate_process:
			self._ensure_worker_ready(force=True)
			return self._worker_ready and not self._worker_disabled

		self._ensure_model_loaded()
		return self._model is not None

	@property
	def is_available(self) -> bool:
		if self._isolate_process:
			return self._worker_ready and not self._worker_disabled
		return self._model is not None

	def close(self) -> None:
		if self._task_queue is not None:
			try:
				self._task_queue.put(None)
			except Exception:
				pass
		self._terminate_worker()
