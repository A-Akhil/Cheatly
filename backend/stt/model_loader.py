# Loads and manages the faster-whisper model from disk or downloads it.
#
# Responsibilities:
# - Read the configured model size and path from config
# - Check if the model files exist locally in models/whisper/
# - Download the model from HuggingFace if not found locally
# - Instantiate the WhisperModel object and return it to whisper_engine.py
# - Handle model loading errors and report them to logger.py
# - Support hot-swapping models when the user changes the model in settings
