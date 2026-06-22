"""Audio capture and processing modules."""
from backend.audio.audio_buffer import AudioBuffer
from backend.audio.microphone import Microphone
from backend.audio.loopback import LoopbackCapture
from backend.audio.source_manager import AudioSourceManager, AudioSourceConfig, AudioSourceType
from backend.audio.device_manager import DeviceManager
from backend.audio.stream_manager import StreamManager

__all__ = [
    "AudioBuffer",
    "Microphone",
    "LoopbackCapture",
    "AudioSourceManager",
    "AudioSourceConfig",
    "AudioSourceType",
    "DeviceManager",
    "StreamManager",
]