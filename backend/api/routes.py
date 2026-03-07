# HTTP route definitions for the Cheatly backend API.
#
# Responsibilities:
# - Define and register all FastAPI HTTP endpoints
# - Expose POST /transcription/start to begin audio capture and transcription
# - Expose POST /transcription/stop to halt audio capture
# - Expose GET /suggestions to retrieve the latest AI suggestions
# - Expose POST /session/reset to clear current context and start a new session
# - Expose GET /models to list available Ollama and API models
# - Delegate business logic to pipeline/ and llm/ modules
# - Return structured JSON responses for all endpoints
