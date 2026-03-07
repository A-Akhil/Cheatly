# Continuously processes incoming audio chunks and produces streaming transcripts.
#
# Responsibilities:
# - Run in a background thread consuming audio chunks from audio_buffer.py
# - Pass each chunk to whisper_engine.py for transcription
# - Append resulting text segments to transcript_buffer.py
# - Operate in streaming mode without waiting for sentence completion
# - Detect silence and use it as a natural segment boundary
# - Emit transcript update events to websocket.py after each chunk is processed
# - Track transcription latency and report it to logging/logger.py
