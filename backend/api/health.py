from __future__ import annotations

from fastapi import APIRouter, Request


def build_health_router() -> APIRouter:
	router = APIRouter(prefix="/health", tags=["health"])

	@router.get("")
	async def health(request: Request) -> dict:
		state = request.app.state.backend
		return {
			"status": "ok",
			"provider": state.config.get("model_provider", {}).get("provider"),
			"session_id": state.session_manager.get().session_id,
			"rag_documents": len(state.kb.list_documents()),
			"audio_running": state.stream_manager.is_running,
			"transcriber_running": state.streaming_transcriber.is_running,
		}

	return router
