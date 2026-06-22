from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketHub:
	def __init__(self) -> None:
		self._connections: set[WebSocket] = set()

	async def connect(self, ws: WebSocket) -> None:
		await ws.accept()
		self._connections.add(ws)
		logger.info(f"WebSocket connected, total: {len(self._connections)}")

	def disconnect(self, ws: WebSocket) -> None:
		self._connections.discard(ws)
		logger.info(f"WebSocket disconnected, total: {len(self._connections)}")

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

	@property
	def connection_count(self) -> int:
		return len(self._connections)


def build_websocket_router(hub: WebSocketHub) -> APIRouter:
	router = APIRouter()

	@router.websocket("/ws")
	async def ws_endpoint(websocket: WebSocket) -> None:
		await hub.connect(websocket)
		try:
			while True:
				data = await websocket.receive_text()
				try:
					msg = json.loads(data)
					msg_type = msg.get("type", "")

					if msg_type == "ping":
						await websocket.send_text(json.dumps({"type": "pong"}))

				except json.JSONDecodeError:
					pass
		except WebSocketDisconnect:
			hub.disconnect(websocket)
		except Exception:
			hub.disconnect(websocket)

	@router.websocket("/ws/suggestions")
	async def ws_suggestions_endpoint(websocket: WebSocket) -> None:
		await hub.connect(websocket)
		try:
			while True:
				data = await websocket.receive_text()
				try:
					msg = json.loads(data)
					msg_type = msg.get("type", "")

					if msg_type == "ping":
						await websocket.send_text(json.dumps({"type": "pong"}))

				except json.JSONDecodeError:
					pass
		except WebSocketDisconnect:
			hub.disconnect(websocket)
		except Exception:
			hub.disconnect(websocket)

	return router
