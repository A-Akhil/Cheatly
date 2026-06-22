from __future__ import annotations

import asyncio
import time
import uuid
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.health import build_health_router
from backend.api.routes import build_routes_router
from backend.api.settings import build_settings_router
from backend.api.websocket import build_websocket_router
from backend.app_state import BackendState
from backend.config.config_loader import ConfigLoader
from backend.logging.logger import configure_logging, get_logger
from backend.utils.system_diagnostics import write_system_diagnostics
from backend.utils.env_loader import load_env_file


def create_app() -> FastAPI:
	project_root = Path(__file__).parent
	load_env_file(project_root / ".env")

	config_dir = project_root / "config"
	config_loader = ConfigLoader(config_dir)
	cfg = config_loader.get_all()

	configure_logging(cfg)
	logger = get_logger("backend.main")

	app = FastAPI(title="Cheatly Backend", version="0.1.0")
	app.add_middleware(
		CORSMiddleware,
		allow_origins=cfg.get("app", {}).get("cors_origins", ["*"]),
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	state = BackendState.build(config_loader)
	app.state.backend = state

	app.include_router(build_routes_router())
	app.include_router(build_health_router())
	app.include_router(build_settings_router())
	app.include_router(build_websocket_router(state.ws_hub))

	@app.middleware("http")
	async def request_logging_middleware(request, call_next):
		request_id = str(uuid.uuid4())[:8]
		start = time.perf_counter()
		logger.info(f"[{request_id}] -> {request.method} {request.url.path}")
		try:
			response = await call_next(request)
			duration_ms = int((time.perf_counter() - start) * 1000)
			logger.info(f"[{request_id}] <- {response.status_code} {request.method} {request.url.path} ({duration_ms}ms)")
			response.headers["X-Request-ID"] = request_id
			return response
		except Exception:
			duration_ms = int((time.perf_counter() - start) * 1000)
			logger.exception(f"[{request_id}] !! {request.method} {request.url.path} failed after {duration_ms}ms")
			raise

	@app.on_event("startup")
	async def startup() -> None:
		loop = asyncio.get_running_loop()
		state.set_event_loop(loop)
		try:
			write_system_diagnostics(state.config)
		except Exception:
			logger.exception("[diag] failed to write system diagnostics")
		stt_cfg = state.config.get("speech_recognition", {})
		require_preload_success = bool(stt_cfg.get("require_preload_success", False))
		if bool(stt_cfg.get("enabled", False)) and bool(stt_cfg.get("preload_on_startup", True)):
			logger.info("[stt] startup preload enabled; waiting for whisper readiness")
			ready = await asyncio.to_thread(state.preload_speech_model)
			if not ready:
				message = "Whisper preload failed during startup; backend will continue with STT unavailable"
				if require_preload_success:
					raise RuntimeError(message)
				logger.error(message)
		logger.info("Backend startup complete")

	@app.on_event("shutdown")
	async def shutdown() -> None:
		state.shutdown()
		logger.info("Backend shutdown complete")

	return app


app = create_app()
