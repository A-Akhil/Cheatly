# In-memory store for temporary session context data.
#
# Responsibilities:
# - Store key-value context items for the current active session
# - Provide get(key) and set(key, value) methods
# - Provide clear() to wipe all memory on session reset
# - Thread-safe access for concurrent reads and writes
# - Not persisted to disk; data lives only for the session duration
