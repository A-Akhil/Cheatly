# Generates AI suggestions from the current transcript and context.
#
# Responsibilities:
# - Receive new transcript segments from transcription_pipeline.py
# - Build a prompt using prompt_builder.py from the latest context
# - Submit the prompt to provider_manager.py for LLM inference
# - Stream parsed suggestions back to websocket.py in real time
# - Deduplicate suggestions that are too similar to recently shown ones
# - Respect the latency budget: target under 2 seconds for suggestion delivery
# - Log suggestion generation latency to logging/logger.py
