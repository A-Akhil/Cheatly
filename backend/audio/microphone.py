# Raw audio capture from the system microphone.
#
# Responsibilities:
# - Open the selected audio input device using sounddevice or pyaudio
# - Capture raw PCM audio in chunks of 500ms to 1000ms duration
# - Push each audio chunk into audio_buffer.py for downstream processing
# - Respect the sample rate and channel settings from configuration
# - Handle device open/close errors with retries and logging
# - Provide start() and stop() methods to control capture lifecycle
# - Emit a callback or queue signal for each captured audio chunk
