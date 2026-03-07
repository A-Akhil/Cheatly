# Handles API-based LLM inference using LiteLLM.
#
# Responsibilities:
# - Use LiteLLM as a unified interface to external model APIs
# - Support OpenAI, Anthropic, Gemini, and any other LiteLLM-compatible provider
# - Read API keys and model names from configuration
# - Send prompts and stream token responses back to the caller
# - Handle API rate limits, timeouts, and error responses
# - Implement the generate(prompt) interface expected by provider_manager.py
# - Track and log inference latency and token usage per request
