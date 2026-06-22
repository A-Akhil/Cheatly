from __future__ import annotations

import faulthandler
import logging
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from .log_formatter import build_text_formatter

_LOGGER_INITIALIZED = False
_FAULT_HANDLER_FILE = None


def configure_logging(config: dict[str, Any]) -> None:
	global _LOGGER_INITIALIZED
	global _FAULT_HANDLER_FILE
	if _LOGGER_INITIALIZED:
		return

	level_name = str(config.get("logging", {}).get("level", "INFO")).upper()
	level = getattr(logging, level_name, logging.INFO)
	app_level_name = str(config.get("logging", {}).get("app_level", level_name)).upper()
	app_level = getattr(logging, app_level_name, level)

	root = logging.getLogger()
	root.setLevel(level)
	formatter = build_text_formatter()

	stream_handler = logging.StreamHandler()
	stream_handler.setFormatter(formatter)
	root.addHandler(stream_handler)

	if bool(config.get("logging", {}).get("log_to_file", True)):
		file_path = Path(config.get("logging", {}).get("file_path", "./backend/logging/backend.log"))
		file_path.parent.mkdir(parents=True, exist_ok=True)
		file_handler = RotatingFileHandler(file_path, maxBytes=4 * 1024 * 1024, backupCount=3)
		file_handler.setFormatter(formatter)
		root.addHandler(file_handler)

		if bool(config.get("logging", {}).get("enable_faulthandler", True)):
			fault_path = Path(config.get("logging", {}).get("fault_file_path", "./backend/logging/backend_fault.log"))
			fault_path.parent.mkdir(parents=True, exist_ok=True)
			_FAULT_HANDLER_FILE = fault_path.open("a", encoding="utf-8")
			faulthandler.enable(file=_FAULT_HANDLER_FILE, all_threads=True)

	# Keep detailed logs for our code, reduce external library noise.
	logging.getLogger("backend").setLevel(app_level)
	logging.getLogger("uvicorn").setLevel(logging.INFO)
	logging.getLogger("uvicorn.error").setLevel(logging.INFO)
	logging.getLogger("uvicorn.access").setLevel(logging.INFO)
	logging.getLogger("LiteLLM").setLevel(logging.WARNING)
	logging.getLogger("litellm").setLevel(logging.WARNING)
	logging.getLogger("httpcore").setLevel(logging.WARNING)
	logging.getLogger("httpx").setLevel(logging.WARNING)
	logging.getLogger("urllib3").setLevel(logging.WARNING)

	def _excepthook(exc_type, exc_value, exc_traceback):
		logging.getLogger("backend.crash").exception(
			"Uncaught exception",
			exc_info=(exc_type, exc_value, exc_traceback),
		)

	def _threading_excepthook(args):
		logging.getLogger("backend.crash").exception(
			f"Uncaught thread exception in {args.thread.name}",
			exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
		)

	sys.excepthook = _excepthook
	threading.excepthook = _threading_excepthook

	_LOGGER_INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
	return logging.getLogger(name)
