from __future__ import annotations

import requests


def is_endpoint_reachable(url: str, timeout_sec: float = 2.0) -> bool:
	try:
		response = requests.get(url, timeout=timeout_sec)
		return response.status_code < 500
	except Exception:
		return False
