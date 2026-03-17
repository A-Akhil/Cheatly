from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile


def build_routes_router() -> APIRouter:
	router = APIRouter(tags=["routes"])

	@router.get("/models")
	async def list_models(request: Request) -> dict:
		cfg = request.app.state.backend.config
		return {
			"provider": cfg.get("model_provider", {}).get("provider"),
			"google_model": cfg.get("model_provider", {}).get("google_model"),
			"google_fallback_model": cfg.get("model_provider", {}).get("google_fallback_model"),
			"ollama_model": cfg.get("model_provider", {}).get("ollama_model"),
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
		state.start_transcription()
		return {"ok": True, "running": state.stream_manager.is_running}

	@router.post("/transcription/stop")
	async def stop_transcription(request: Request) -> dict:
		state = request.app.state.backend
		state.stop_transcription()
		return {"ok": True, "running": state.stream_manager.is_running}

	@router.get("/transcription/status")
	async def transcription_status(request: Request) -> dict:
		state = request.app.state.backend
		return {
			"running": state.stream_manager.is_running,
			"transcriber_running": state.streaming_transcriber.is_running,
			"segments": state.transcript_buffer.get_all()[-20:],
		}

	@router.post("/transcript/ingest")
	async def ingest_transcript(request: Request, payload: dict) -> dict:
		text = str(payload.get("text", "")).strip()
		if not text:
			raise HTTPException(status_code=400, detail="text is required")

		state = request.app.state.backend
		state.transcription_pipeline.ingest_text(text)
		result = state.suggestion_engine.generate_suggestions(text)
		await state.ws_hub.broadcast({"type": "suggestions", "payload": result})
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

	return router
