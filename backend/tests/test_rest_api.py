"""Tests for REST API endpoints."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from backend.main import app
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"


class TestModelsEndpoint:
    """Tests for /models endpoint."""

    def test_models_returns_litellm_config(self, client):
        response = client.get("/models")
        assert response.status_code == 200
        data = response.json()
        assert "provider" in data
        assert "model" in data
        assert "fallback_model" in data
        assert data["provider"] == "litellm"


class TestSettingsEndpoint:
    """Tests for /settings endpoint."""

    def test_update_model_settings(self, client):
        payload = {
            "model_provider": {
                "model": "gpt-4-turbo",
                "fallback_model": "ollama/mistral"
            }
        }
        response = client.post("/settings", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True

    def test_update_trigger_preset(self, client):
        payload = {
            "trigger": {
                "preset": "fast"
            }
        }
        response = client.post("/settings", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True

    def test_invalid_preset_still_returns_ok(self, client):
        payload = {
            "trigger": {
                "preset": "nonexistent"
            }
        }
        response = client.post("/settings", json=payload)
        assert response.status_code == 200


class TestTranscriptEndpoint:
    """Tests for /transcript/ingest endpoint."""

    def test_ingest_requires_text(self, client):
        response = client.post("/transcript/ingest", json={})
        assert response.status_code == 400

    def test_ingest_empty_text_fails(self, client):
        response = client.post("/transcript/ingest", json={"text": ""})
        assert response.status_code == 400

    def test_ingest_valid_text_returns_result(self, client):
        response = client.post("/transcript/ingest", json={"text": "Hello world"})
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True
        assert "result" in data


class TestRagEndpoints:
    """Tests for /rag/* endpoints."""

    def test_list_documents(self, client):
        response = client.get("/rag/documents")
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert isinstance(data["documents"], list)

    def test_ingest_text_requires_text(self, client):
        response = client.post("/rag/documents/text", json={})
        assert response.status_code == 400

    def test_ingest_text_valid(self, client):
        response = client.post("/rag/documents/text", json={
            "source_name": "test-doc",
            "text": "This is test content for RAG."
        })
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True
        assert "document_id" in data


class TestTranscriptionEndpoints:
    """Tests for /transcription/* endpoints."""

    def test_transcription_status(self, client):
        response = client.get("/transcription/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data
        assert "transcriber_running" in data

    def test_start_transcription(self, client):
        response = client.post("/transcription/start")
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True

        client.post("/transcription/stop")

    def test_stop_transcription(self, client):
        response = client.post("/transcription/stop")
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True


class TestSessionEndpoints:
    """Tests for /session/* endpoints."""

    def test_reset_session(self, client):
        response = client.post("/session/reset")
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True
        assert "session_id" in data


class TestAudioDevicesEndpoint:
    """Tests for /audio/devices endpoint."""

    def test_list_audio_devices(self, client):
        response = client.get("/audio/devices")
        assert response.status_code == 200
        data = response.json()
        assert "microphones" in data
        assert "loopback" in data
        assert isinstance(data["microphones"], list)
        assert isinstance(data["loopback"], list)
