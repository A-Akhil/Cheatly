# Threading utility helpers used across the backend.
#
# Responsibilities:
# - Provide a managed background thread wrapper with start/stop/restart support
# - Implement a safe thread-safe event flag for signaling between threads
# - Provide a periodic task runner that executes a function at a fixed interval
# - Used by audio/stream_manager.py and stt/streaming_transcriber.py
