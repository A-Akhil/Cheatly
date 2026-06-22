from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

_API_KEY_ENV_MAP = {
	"openai": "OPENAI_API_KEY",
	"anthropic": "ANTHROPIC_API_KEY",
	"gemini": "GOOGLE_API_KEY",
	"google": "GOOGLE_API_KEY",
	"azure": "AZURE_API_KEY",
}


def build_settings_router() -> APIRouter:
	router = APIRouter(prefix="/settings", tags=["settings"])

	@router.get("")
	async def get_settings(request: Request) -> dict:
		return request.app.state.backend.config_loader.get_all()

	@router.post("")
	async def update_settings(request: Request, payload: dict) -> dict:
		state = request.app.state.backend

		# Apply API key to environment if provided so LiteLLM can authenticate
		mp = payload.get("model_provider", {})
		api_key = str(mp.get("api_key", "")).strip()
		provider = str(mp.get("provider", "")).lower()
		if api_key:
			env_var = _API_KEY_ENV_MAP.get(provider)
			if env_var:
				os.environ[env_var] = api_key
				logger.info(f"[settings] set {env_var} from incoming api_key")
			# Remove api_key from payload before saving to config file (don't persist secrets)
			mp.pop("api_key", None)

		updated = state.config_loader.save_user_overrides(payload)
		state.reload_config(updated)
		return {"ok": True, "config": updated}

	return router
