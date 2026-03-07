# Constructs LLM prompts from conversation context and transcript input.
#
# Responsibilities:
# - Accept the recent transcript text and conversation history as input
# - Build a structured prompt that instructs the model to generate suggestions
# - Include a system prompt that defines the assistant behavior and output format
# - Inject relevant context from context_manager.py into the prompt
# - Format the prompt according to the selected model's expected template
# - Keep prompts concise to minimize inference latency
# - Return the final prompt string ready for submission to provider_manager.py
