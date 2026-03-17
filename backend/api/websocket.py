from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect


class WebSocketHub:
	def __init__(self) -> None:
		self._connections: set[WebSocket] = set()

	async def connect(self, ws: WebSocket) -> None:
		await ws.accept()
		self._connections.add(ws)

	def disconnect(self, ws: WebSocket) -> None:
		self._connections.discard(ws)

	async def broadcast(self, payload: dict[str, Any]) -> None:
		disconnected: list[WebSocket] = []
		message = json.dumps(payload)
		for ws in self._connections:
			try:
				await ws.send_text(message)
			except Exception:
				disconnected.append(ws)
		for ws in disconnected:
			self.disconnect(ws)


def build_websocket_router(hub: WebSocketHub) -> APIRouter:
	router = APIRouter()

	@router.websocket("/ws")
	async def ws_endpoint(websocket: WebSocket) -> None:
		await hub.connect(websocket)
		try:
			while True:
				await websocket.receive_text()
		except WebSocketDisconnect:
			hub.disconnect(websocket)
		except Exception:
			hub.disconnect(websocket)

	return router
