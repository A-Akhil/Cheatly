# Stores incremental transcript segments produced by streaming_transcriber.py.
#
# Responsibilities:
# - Maintain an ordered list of transcript segments with timestamps
# - Provide append() to add new segments from the transcriber
# - Provide get_recent(n_seconds) to return segments from the last N seconds
# - Provide get_full() to return the complete transcript for the session
# - Emit an event or callback when a new segment is appended
# - Thread-safe access for concurrent reads from context_manager.py and websocket.py
