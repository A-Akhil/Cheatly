# Detects and manages available audio input devices.
#
# Responsibilities:
# - Enumerate all available microphone and audio input devices on the system
# - Return device names, IDs, and capabilities (sample rate, channels)
# - Select the default input device if no device is configured
# - Detect device changes (plug/unplug) and notify stream_manager.py
# - Support device selection by name or device index
# - Cross-platform: work on Linux (ALSA/PulseAudio), Windows (WASAPI), macOS (CoreAudio)
