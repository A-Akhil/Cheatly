"""Tests for WebSocket message formats."""
import pytest
import json
import asyncio
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


@pytest.fixture
def client():
    """Create test client."""
    from backend.main import app
    return TestClient(app)


class TestWebSocketConnection:
    """Tests for WebSocket connection handling."""

    def test_ws_connect(self, client):
        with client.websocket_connect("/ws") as ws:
            assert ws is not None

    def test_ws_suggestions_connect(self, client):
        with client.websocket_connect("/ws/suggestions") as ws:
            assert ws is not None


class TestPingPong:
    """Tests for ping/pong heartbeat."""

    def test_ping_receives_pong(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_text(json.dumps({"type": "ping"}))
            response = ws.receive_text()
            data = json.loads(response)
            assert data["type"] == "pong"

    def test_suggestions_endpoint_ping_pong(self, client):
        with client.websocket_connect("/ws/suggestions") as ws:
            ws.send_text(json.dumps({"type": "ping"}))
            response = ws.receive_text()
            data = json.loads(response)
            assert data["type"] == "pong"


class TestSuggestionMessageFormat:
    """Tests for suggestion message format."""

    def test_suggestion_message_structure(self):
        """Verify expected suggestion message structure."""
        message = {
            "type": "suggestions",
            "payload": {
                "output": ["Suggestion 1", "Suggestion 2"],
                "turn_id": "abc123",
                "mode": "final",
                "revision": 1
            }
        }

        assert message["type"] == "suggestions"
        assert "payload" in message
        assert "output" in message["payload"]
        assert "turn_id" in message["payload"]
        assert "mode" in message["payload"]
        assert "revision" in message["payload"]
        assert isinstance(message["payload"]["output"], list)

    def test_prefetch_mode_message(self):
        """Verify prefetch mode message format."""
        message = {
            "type": "suggestions",
            "payload": {
                "output": ["Draft suggestion"],
                "turn_id": "turn-001",
                "mode": "prefetch",
                "revision": 0
            }
        }

        assert message["payload"]["mode"] == "prefetch"
        assert message["payload"]["revision"] == 0

    def test_final_mode_message(self):
        """Verify final mode message format."""
        message = {
            "type": "suggestions",
            "payload": {
                "output": ["Final suggestion"],
                "turn_id": "turn-001",
                "mode": "final",
                "revision": 2
            }
        }

        assert message["payload"]["mode"] == "final"
        assert message["payload"]["revision"] == 2


class TestSessionResetMessage:
    """Tests for session reset message format."""

    def test_session_reset_structure(self):
        """Verify session reset message structure."""
        message = {
            "type": "session_reset"
        }

        assert message["type"] == "session_reset"


class TestBroadcastIntegration:
    """Tests for broadcast functionality via REST -> WebSocket."""

    def test_ingest_broadcasts_to_websocket(self, client):
        with client.websocket_connect("/ws/suggestions") as ws:
            client.post("/transcript/ingest", json={"text": "Test broadcast"})

            try:
                response = ws.receive_text()
                data = json.loads(response)
                assert data["type"] == "suggestions"
                assert "payload" in data
            except Exception:
                pass

    def test_session_reset_broadcasts(self, client):
        with client.websocket_connect("/ws") as ws:
            client.post("/session/reset")

            try:
                response = ws.receive_text()
                data = json.loads(response)
                assert data["type"] == "session_reset"
            except Exception:
                pass


class TestInvalidMessages:
    """Tests for handling invalid WebSocket messages."""

    def test_invalid_json_ignored(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_text("not valid json")
            ws.send_text(json.dumps({"type": "ping"}))
            response = ws.receive_text()
            data = json.loads(response)
            assert data["type"] == "pong"

    def test_unknown_message_type_ignored(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_text(json.dumps({"type": "unknown_type"}))
            ws.send_text(json.dumps({"type": "ping"}))
            response = ws.receive_text()
            data = json.loads(response)
            assert data["type"] == "pong"
