"""Unified audio source manager for mic + loopback capture."""
from __future__ import annotations

import logging
import threading
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum

from backend.audio.audio_buffer import AudioBuffer
from backend.audio.microphone import Microphone
from backend.audio.loopback import LoopbackCapture
from backend.models.audio_chunk import AudioChunk

logger = logging.getLogger(__name__)


class AudioSourceType(Enum):
    MIC = "mic"
    MEETING = "meeting"
    BOTH = "both"


@dataclass
class AudioSourceConfig:
    """Configuration for audio sources."""
    enable_mic: bool = True
    enable_loopback: bool = True
    mic_device_index: Optional[int] = None
    loopback_device_id: Optional[str] = None
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration_ms: int = 100


class AudioSourceManager:
    """Manages multiple audio sources and routes them to appropriate handlers."""

    def __init__(
        self,
        config: AudioSourceConfig,
        on_audio_chunk: Callable[[AudioChunk], None],
    ) -> None:
        """Initialize the audio source manager.

        Args:
            config: Audio source configuration.
            on_audio_chunk: Callback receiving tagged AudioChunk objects.
        """
        self._config = config
        self._on_audio_chunk = on_audio_chunk
        self._lock = threading.Lock()
        self._running = False

        self._mic_buffer: Optional[AudioBuffer] = None
        self._microphone: Optional[Microphone] = None
        self._loopback: Optional[LoopbackCapture] = None
        self._mic_thread: Optional[threading.Thread] = None

    def _on_mic_audio(self, data: bytes) -> None:
        """Handle audio from microphone."""
        chunk = AudioChunk(
            data=data,
            sample_rate=self._config.sample_rate,
            channels=self._config.channels,
            source="mic",
        )
        self._on_audio_chunk(chunk)

    def _on_loopback_audio(self, data: bytes, source: str) -> None:
        """Handle audio from loopback capture."""
        chunk = AudioChunk(
            data=data,
            sample_rate=self._config.sample_rate,
            channels=self._config.channels,
            source=source,
        )
        self._on_audio_chunk(chunk)

    def _mic_poll_loop(self) -> None:
        """Poll microphone buffer and emit chunks."""
        import time
        while self._running and self._mic_buffer:
            chunk = self._mic_buffer.pop()
            if chunk:
                self._on_mic_audio(chunk)
            else:
                time.sleep(0.01)

    def start(self) -> None:
        """Start all enabled audio sources."""
        logger.info(
            "[audio] source_manager.start "
            f"enable_mic={self._config.enable_mic} enable_loopback={self._config.enable_loopback} "
            f"sample_rate={self._config.sample_rate} channels={self._config.channels} "
            f"chunk_ms={self._config.chunk_duration_ms}"
        )
        with self._lock:
            if self._running:
                return
            self._running = True

        if self._config.enable_mic:
            try:
                self._mic_buffer = AudioBuffer()
                self._microphone = Microphone(
                    audio_buffer=self._mic_buffer,
                    sample_rate=self._config.sample_rate,
                    channels=self._config.channels,
                    chunk_duration_ms=self._config.chunk_duration_ms,
                    device_index=self._config.mic_device_index,
                )
                self._microphone.start()
                self._mic_thread = threading.Thread(target=self._mic_poll_loop, daemon=True)
                self._mic_thread.start()
                logger.info("[audio] microphone capture started")
            except Exception:
                logger.exception("[audio] microphone capture failed to start")

        if self._config.enable_loopback:
            try:
                self._loopback = LoopbackCapture(
                    on_audio=self._on_loopback_audio,
                    sample_rate=self._config.sample_rate,
                    channels=self._config.channels,
                    chunk_duration_ms=self._config.chunk_duration_ms,
                    device_id=self._config.loopback_device_id,
                )
                self._loopback.start()
                logger.info("[audio] loopback capture started")
            except Exception:
                logger.exception("[audio] loopback capture failed to start")

    def stop(self) -> None:
        """Stop all audio sources."""
        logger.info("[audio] source_manager.stop begin")
        with self._lock:
            self._running = False

        if self._microphone:
            self._microphone.stop()
            self._microphone = None

        if self._mic_thread:
            self._mic_thread.join(timeout=1.0)
            self._mic_thread = None

        if self._loopback:
            self._loopback.stop()
            self._loopback = None

        self._mic_buffer = None
        logger.info("[audio] source_manager.stop complete")

    @property
    def is_running(self) -> bool:
        return self._running

    def list_devices(self) -> dict:
        """List available input devices."""
        devices = {
            "microphones": [],
            "loopback": [],
        }

        try:
            import sounddevice as sd
            for i, dev in enumerate(sd.query_devices()):
                if dev["max_input_channels"] > 0:
                    devices["microphones"].append({
                        "id": i,
                        "name": dev["name"],
                        "sample_rate": int(dev["default_samplerate"]),
                        "channels": dev["max_input_channels"],
                    })
        except Exception as e:
            logger.warning(f"Failed to list microphones: {e}")

        devices["loopback"] = LoopbackCapture.list_loopback_devices()
        return devices
