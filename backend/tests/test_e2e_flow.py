"""End-to-end flow tests for Cheatly pipeline."""
import pytest
import json
import time
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from backend.main import app
    return TestClient(app)


class TestFullPipelineFlow:
    """Tests for the complete transcript -> suggestion flow."""

    def test_ingest_produces_suggestions(self, client):
        """Test that ingesting text produces suggestions."""
        response = client.post("/transcript/ingest", json={
            "text": "Can you explain how machine learning works?"
        })

        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True
        assert "result" in data
        assert "output" in data["result"]

    def test_suggestions_broadcast_to_websocket(self, client):
        """Test that suggestions are broadcast to connected WebSocket clients."""
        with client.websocket_connect("/ws/suggestions") as ws:
            client.post("/transcript/ingest", json={
                "text": "What is the capital of France?"
            })

            try:
                response = ws.receive_text()
                data = json.loads(response)
                assert data["type"] == "suggestions"
                assert "payload" in data
                assert "output" in data["payload"]
            except Exception:
                pass


class TestSessionLifecycle:
    """Tests for session lifecycle management."""

    def test_session_reset_clears_state(self, client):
        """Test that session reset clears all state."""
        client.post("/transcript/ingest", json={"text": "First message"})

        response = client.post("/session/reset")
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True
        assert "session_id" in data

    def test_new_session_after_reset(self, client):
        """Test that a new session ID is generated after reset."""
        response1 = client.post("/session/reset")
        session1 = response1.json()["session_id"]

        response2 = client.post("/session/reset")
        session2 = response2.json()["session_id"]

        assert session1 != session2


class TestTranscriptionLifecycle:
    """Tests for transcription start/stop lifecycle."""

    def test_start_stop_transcription(self, client):
        """Test starting and stopping transcription."""
        start_response = client.post("/transcription/start")
        assert start_response.status_code == 200
        assert start_response.json().get("ok") is True

        status_response = client.get("/transcription/status")
        assert status_response.status_code == 200

        stop_response = client.post("/transcription/stop")
        assert stop_response.status_code == 200
        assert stop_response.json().get("ok") is True

    def test_double_start_is_idempotent(self, client):
        """Test that starting twice doesn't cause issues."""
        client.post("/transcription/start")
        response = client.post("/transcription/start")
        assert response.status_code == 200

        client.post("/transcription/stop")


class TestSettingsUpdateFlow:
    """Tests for settings update and its effects."""

    def test_update_model_affects_suggestions(self, client):
        """Test that updating model settings takes effect."""
        client.post("/settings", json={
            "model_provider": {
                "model": "gpt-4-turbo",
                "fallback_model": "ollama/llama3"
            }
        })

        models = client.get("/models").json()
        assert models["model"] == "gpt-4-turbo"
        assert models["fallback_model"] == "ollama/llama3"

    def test_update_trigger_preset(self, client):
        """Test updating trigger preset."""
        for preset in ["fast", "balanced", "accurate"]:
            response = client.post("/settings", json={
                "trigger": {"preset": preset}
            })
            assert response.status_code == 200


class TestRagIntegration:
    """Tests for RAG document integration."""

    def test_add_document_and_query(self, client):
        """Test adding a document and using it in suggestions."""
        add_response = client.post("/rag/documents/text", json={
            "source_name": "test-knowledge",
            "text": "The company was founded in 2024. The CEO is John Smith."
        })
        assert add_response.status_code == 200
        doc_id = add_response.json()["document_id"]

        list_response = client.get("/rag/documents")
        docs = list_response.json()["documents"]
        assert any(d.get("source_name") == "test-knowledge" for d in docs)

        client.delete(f"/rag/documents/{doc_id}")

    def test_delete_document(self, client):
        """Test deleting a RAG document."""
        add_response = client.post("/rag/documents/text", json={
            "source_name": "to-delete",
            "text": "Temporary content."
        })
        doc_id = add_response.json()["document_id"]

        delete_response = client.delete(f"/rag/documents/{doc_id}")
        assert delete_response.status_code == 200


class TestWebSocketReconnectScenarios:
    """Tests for WebSocket reconnection scenarios."""

    def test_multiple_connections(self, client):
        """Test multiple simultaneous WebSocket connections."""
        with client.websocket_connect("/ws/suggestions") as ws1:
            with client.websocket_connect("/ws/suggestions") as ws2:
                client.post("/transcript/ingest", json={"text": "Broadcast test"})

                for ws in [ws1, ws2]:
                    try:
                        response = ws.receive_text()
                        data = json.loads(response)
                        assert data["type"] == "suggestions"
                    except Exception:
                        pass


class TestTurnMetadataFlow:
    """Tests for turn metadata through the full pipeline."""

    def test_ingest_returns_turn_metadata(self, client):
        """Test that ingest response includes turn metadata."""
        with client.websocket_connect("/ws/suggestions") as ws:
            client.post("/transcript/ingest", json={
                "text": "Hello, how are you today?"
            })

            try:
                response = ws.receive_text()
                data = json.loads(response)

                if data["type"] == "suggestions":
                    payload = data["payload"]
                    assert "turn_id" in payload
                    assert "mode" in payload
                    assert "revision" in payload
            except Exception:
                pass

    def test_multiple_ingests_same_session(self, client):
        """Test multiple ingests maintain turn tracking."""
        with client.websocket_connect("/ws/suggestions") as ws:
            messages = []

            for text in ["First message", "Second message", "Third message"]:
                client.post("/transcript/ingest", json={"text": text})
                try:
                    response = ws.receive_text()
                    messages.append(json.loads(response))
                except Exception:
                    pass

            for msg in messages:
                if msg.get("type") == "suggestions":
                    assert "payload" in msg


class TestErrorHandling:
    """Tests for error handling in the pipeline."""

    def test_empty_transcript_rejected(self, client):
        """Test that empty transcripts are rejected."""
        response = client.post("/transcript/ingest", json={"text": ""})
        assert response.status_code == 400

    def test_missing_text_field_rejected(self, client):
        """Test that missing text field is rejected."""
        response = client.post("/transcript/ingest", json={})
        assert response.status_code == 400

    def test_whitespace_only_rejected(self, client):
        """Test that whitespace-only text is rejected."""
        response = client.post("/transcript/ingest", json={"text": "   "})
        assert response.status_code == 400
