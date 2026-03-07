# Stores and retrieves the full transcript history for the session.
#
# Responsibilities:
# - Persist all transcript segments produced during the current session
# - Provide append(segment) to add new transcript entries
# - Provide get_all() and get_since(timestamp) for retrieval
# - Optionally persist history to disk for post-session review
# - Provide clear() for session reset
# - Used by context_manager.py when building the prompt context window
