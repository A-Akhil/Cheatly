# Central logger for the Cheatly backend.
#
# Responsibilities:
# - Initialize a structured logger using Python logging or loguru
# - Support configurable log levels (debug, info, warning, error)
# - Write logs to stdout and optionally to a rotating file in the app data directory
# - Expose log_metric(name, value_ms) to record latency measurements
# - Used by all backend modules for consistent log output
# - Format log entries using log_formatter.py
