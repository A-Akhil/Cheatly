# Manages the lifecycle of conversation sessions.
#
# Responsibilities:
# - Create a new session with a unique ID and start timestamp
# - Reset all context on session start: clear memory_store, transcript_history, context_manager
# - Track session duration and status (active, paused, ended)
# - Expose start_session(), pause_session(), resume_session(), end_session() methods
# - Notify relevant pipeline components when session state changes
# - Provide current session metadata to health.py and websocket.py
