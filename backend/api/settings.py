# Settings API endpoint for reading and writing user configuration.
#
# Responsibilities:
# - Expose GET /settings to return current user configuration
# - Expose POST /settings to update and persist user configuration
# - Validate incoming configuration values before applying them
# - Trigger model provider reload when model selection changes
# - Trigger audio device reload when device settings change
# - Persist changes to config/user_config.yaml via config_loader.py
# - Return validation errors if submitted settings are invalid
