from __future__ import annotations

import logging


def build_text_formatter() -> logging.Formatter:
	return logging.Formatter(
		fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
		datefmt="%Y-%m-%d %H:%M:%S",
	)
