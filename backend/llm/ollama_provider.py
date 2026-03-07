# Handles local LLM inference through Ollama.
#
# Responsibilities:
# - Connect to the locally running Ollama HTTP server (default: localhost:11434)
# - Send prompt requests to the Ollama /api/generate endpoint
# - Stream response tokens back as they are generated
# - Support model selection from the list of locally pulled Ollama models
# - Handle connection errors if Ollama is not running and report them
# - Implement the generate(prompt) interface expected by provider_manager.py
# - Track and log inference latency for each request
