from __future__ import annotations

from pathlib import Path
from urllib.parse import urljoin
import logging
import asyncio

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
import requests
from backend.utils.system_diagnostics import collect_system_diagnostics

logger = logging.getLogger(__name__)


def build_routes_router() -> APIRouter:
	router = APIRouter(tags=["routes"])

	@router.get("/models")
	async def list_models(request: Request) -> dict:
		cfg = request.app.state.backend.config
		model_cfg = cfg.get("model_provider", {})
		return {
			"provider": model_cfg.get("provider", "litellm"),
			"model": model_cfg.get("model", "gpt-4"),
			"fallback_model": model_cfg.get("fallback_model", "ollama/llama3"),
		}

	@router.get("/providers/ollama/models")
	async def list_ollama_models(request: Request, api_base: str | None = None) -> dict:
		state = request.app.state.backend
		model_cfg = state.config.get("model_provider", {})

		base = (api_base or model_cfg.get("api_base") or "http://127.0.0.1:11434").strip().rstrip("/") + "/"
		tags_url = urljoin(base, "api/tags")

		try:
			resp = requests.get(tags_url, timeout=4)
			resp.raise_for_status()
			payload = resp.json()
		except Exception as exc:
			raise HTTPException(status_code=502, detail=f"Failed to fetch ollama models from {tags_url}: {exc}") from exc

		models: list[str] = []
		for item in payload.get("models", []):
			name = str(item.get("name", "")).strip()
			if name:
				models.append(f"ollama/{name}")

		seen: set[str] = set()
		unique_models = [m for m in models if not (m in seen or seen.add(m))]

		return {
			"api_base": base.rstrip("/"),
			"models": unique_models,
		}


	@router.post("/session/reset")
	async def reset_session(request: Request) -> dict:
		state = request.app.state.backend
		state.reset_session()
		await state.ws_hub.broadcast({"type": "session_reset"})
		return {"ok": True, "session_id": state.session_manager.get().session_id}

	@router.post("/transcription/start")
	async def start_transcription(request: Request) -> dict:
		state = request.app.state.backend
		logger.info("[stt] POST /transcription/start received")
		try:
			state.start_transcription()
		except RuntimeError as exc:
			raise HTTPException(status_code=503, detail=str(exc)) from exc
		logger.info(f"[stt] POST /transcription/start done running={state.stream_manager.is_running}")
		return {"ok": True, "running": state.stream_manager.is_running}

	@router.post("/transcription/stop")
	async def stop_transcription(request: Request) -> dict:
		state = request.app.state.backend
		logger.info("[stt] POST /transcription/stop received")
		state.stop_transcription()
		logger.info(f"[stt] POST /transcription/stop done running={state.stream_manager.is_running}")
		return {"ok": True, "running": state.stream_manager.is_running}

	@router.get("/transcription/status")
	async def transcription_status(request: Request) -> dict:
		state = request.app.state.backend
		state.stt_available = bool(state.streaming_transcriber.whisper.is_available)
		return {
			"running": state.stream_manager.is_running,
			"transcriber_running": state.streaming_transcriber.is_running,
			"stt_available": state.stt_available,
			"stt_preload_ready": state.stt_preload_ready,
			"segments": state.transcript_buffer.get_all()[-20:],
		}

	@router.post("/transcript/ingest")
	async def ingest_transcript(request: Request, payload: dict) -> dict:
		text = str(payload.get("text", "")).strip()
		if not text:
			raise HTTPException(status_code=400, detail="text is required")

		state = request.app.state.backend
		segment = state.transcript_buffer.append(text)
		if segment is None:
			raise HTTPException(status_code=400, detail="Failed to create transcript segment")
		result = await asyncio.to_thread(
			state.suggestion_engine.generate_suggestions,
			text,
			turn_id=segment.turn_id,
			mode="final",
		)

		await state.ws_hub.broadcast({
			"type": "suggestions",
			"payload": {
				"output": result.get("suggestions", result.get("output", [])),
				"turn_id": segment.turn_id,
				"mode": "final",
				"revision": segment.revision,
			}
		})
		return {"ok": True, "result": result}

	@router.get("/rag/documents")
	async def list_rag_documents(request: Request) -> dict:
		return {"documents": request.app.state.backend.kb.list_documents()}

	@router.post("/rag/documents/text")
	async def ingest_rag_text(request: Request, payload: dict) -> dict:
		source_name = str(payload.get("source_name", "manual-text")).strip() or "manual-text"
		text = str(payload.get("text", "")).strip()
		if not text:
			raise HTTPException(status_code=400, detail="text is required")
		doc_id = request.app.state.backend.kb.ingest_text(source_name, text)
		return {"ok": True, "document_id": doc_id}

	@router.post("/rag/documents/file")
	async def ingest_rag_file(request: Request, file: UploadFile = File(...)) -> dict:
		data = await file.read()
		if not data:
			raise HTTPException(status_code=400, detail="uploaded file is empty")

		suffix = Path(file.filename or "").suffix.lower()
		if suffix not in {".txt", ".md", ".rst", ".log", ".json", ".csv"}:
			raise HTTPException(status_code=400, detail="unsupported file extension")

		text = data.decode("utf-8", errors="ignore")
		doc_id = request.app.state.backend.kb.ingest_text(file.filename or "uploaded-file", text)
		return {"ok": True, "document_id": doc_id}

	@router.delete("/rag/documents/{document_id}")
	async def delete_rag_document(request: Request, document_id: str) -> dict:
		request.app.state.backend.kb.delete_document(document_id)
		return {"ok": True}

	@router.get("/audio/devices")
	async def list_audio_devices(request: Request) -> dict:
		from backend.audio.source_manager import AudioSourceManager, AudioSourceConfig
		mgr = AudioSourceManager(AudioSourceConfig(), lambda x: None)
		return mgr.list_devices()

	@router.get("/debug/system")
	async def debug_system(request: Request) -> dict:
		state = request.app.state.backend
		return collect_system_diagnostics(state.config)

	return router
