# Faster-Whisper inference engine wrapper.
#
# Responsibilities:
# - Load the faster-whisper model using the path from config
# - Support model sizes: tiny, base, small, medium, large-v3
# - Run transcription on audio chunks provided as numpy arrays
# - Return transcribed text segments with timestamps and confidence scores
# - Support GPU inference via CTranslate2 if CUDA is available
# - Fall back to CPU inference if no GPU is detected
# - Expose a transcribe(audio_chunk) method used by streaming_transcriber.py
