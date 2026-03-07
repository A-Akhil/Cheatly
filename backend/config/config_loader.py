# Configuration loader that merges default and user configuration files.
#
# Responsibilities:
# - Load default_config.yaml as the base configuration
# - Load user_config.yaml and merge it on top, overriding defaults
# - Expose a get(key) interface for all backend modules to read config values
# - Watch user_config.yaml for changes and hot-reload when it is updated
# - Validate config values against expected types and allowed values
# - Raise clear errors if required config keys are missing or invalid
