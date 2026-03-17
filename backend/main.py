from __future__ import annotations

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

	@app.on_event("startup")
	async def startup() -> None:
		logger.info("Backend startup complete")

	@app.on_event("shutdown")
	async def shutdown() -> None:
		logger.info("Backend shutdown complete")

	return app


app = create_app()
