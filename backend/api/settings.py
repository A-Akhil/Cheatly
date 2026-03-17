from __future__ import annotations

from fastapi import APIRouter, Request


def build_settings_router() -> APIRouter:
	router = APIRouter(prefix="/settings", tags=["settings"])

	@router.get("")
	async def get_settings(request: Request) -> dict:
		return request.app.state.backend.config_loader.get_all()

	@router.post("")
	async def update_settings(request: Request, payload: dict) -> dict:
		state = request.app.state.backend
		updated = state.config_loader.save_user_overrides(payload)
		state.reload_config(updated)
		return {"ok": True, "config": updated}

	return router
