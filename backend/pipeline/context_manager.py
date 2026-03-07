# Maintains and manages the conversation context window.
#
# Responsibilities:
# - Store recent transcript segments and AI suggestion history
# - Enforce a maximum context window size to stay within model token limits
# - Evict oldest context entries when the window is full
# - Provide get_context() returning a structured context object for prompt_builder.py
# - Support context reset when a new session starts via session_manager.py
# - Integrate with memory_store.py and transcript_history.py for persistence
