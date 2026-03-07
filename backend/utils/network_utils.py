# Network utility helpers for backend connectivity checks.
#
# Responsibilities:
# - Check if a local port is available before starting the FastAPI server
# - Check if the Ollama server is reachable before attempting inference
# - Provide a retry wrapper for HTTP requests with configurable backoff
# - Used by main.py and ollama_provider.py at startup
