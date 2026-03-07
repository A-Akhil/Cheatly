# Controls the flow and state of the audio streaming pipeline.
#
# Responsibilities:
# - Coordinate between microphone.py and audio_buffer.py
# - Manage start, pause, resume, and stop states of the audio stream
# - Ensure audio chunks are forwarded to the buffer without dropping frames
# - Handle stream overflow events and log audio underrun conditions
# - Provide stream status to health.py for reporting
