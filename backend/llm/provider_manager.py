# Selects and routes requests to the correct LLM provider.
#
# Responsibilities:
# - Read model provider setting from configuration (ollama or api)
# - Instantiate the appropriate provider: ollama_provider.py or api_provider.py
# - Expose a unified generate(prompt) interface used by suggestion_engine.py
# - Support switching providers at runtime when settings change
# - Handle provider initialization errors and fall back gracefully
# - Report provider status to health.py
