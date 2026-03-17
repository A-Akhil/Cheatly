from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from .log_formatter import build_text_formatter

_LOGGER_INITIALIZED = False


def configure_logging(config: dict[str, Any]) -> None:
	global _LOGGER_INITIALIZED
	if _LOGGER_INITIALIZED:
		return

	level_name = str(config.get("logging", {}).get("level", "INFO")).upper()
	level = getattr(logging, level_name, logging.INFO)

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

	_LOGGER_INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
	return logging.getLogger(name)
