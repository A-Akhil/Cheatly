# Rolling audio buffer that stores recent audio chunks for transcription.
#
# Responsibilities:
# - Maintain a thread-safe circular buffer of recent raw audio chunks
# - Accept new chunks pushed from microphone.py
# - Expose a method for streaming_transcriber.py to consume chunks
# - Discard oldest chunks when buffer exceeds the maximum size limit
# - Support configurable buffer length in seconds
# - Provide a drain() method to flush all pending audio chunks
