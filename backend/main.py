# Entry point for the Cheatly Python AI backend.
#
# Responsibilities:
# - Load and validate system configuration from config/
# - Initialize and start the FastAPI application server
# - Load the faster-whisper speech recognition model into memory
# - Initialize model providers (Ollama for local, LiteLLM for API-based)
# - Start background audio capture threads from audio/microphone.py
# - Register WebSocket stream handlers from api/websocket.py
# - Register all HTTP route handlers from api/routes.py
# - Run the uvicorn ASGI server on localhost at a fixed port
# - Keep the process alive as long as the Tauri desktop app is running
