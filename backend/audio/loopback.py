"""WASAPI loopback capture for capturing system/meeting audio on Windows.

Uses pyaudiowpatch for WASAPI loopback support.
"""
from __future__ import annotations

import threading
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class LoopbackCapture:
    """Captures system audio via WASAPI loopback (Windows only)."""

    def __init__(
        self,
        on_audio: Callable[[bytes, str], None],
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_duration_ms: int = 100,
        device_id: Optional[str] = None,
    ) -> None:
        """Initialize loopback capture.

        Args:
            on_audio: Callback receiving (audio_bytes, source_tag).
            sample_rate: Target sample rate (will resample if needed).
            channels: Number of channels (1=mono, 2=stereo).
            chunk_duration_ms: Chunk size in milliseconds.
            device_id: Specific loopback device ID, or None for default.
        """
        self._on_audio = on_audio
        self._sample_rate = sample_rate
        self._channels = channels
        self._chunk_duration_ms = chunk_duration_ms
        self._device_id = device_id

        self._running = False
        self._stream = None
        self._pyaudio = None
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    def _find_loopback_device(self, p) -> Optional[dict]:
        """Find a WASAPI loopback device."""
        # pyaudiowpatch does not expose paWASAPI constant - find WASAPI host API by name
        wasapi_host_api_index = None
        try:
            for i in range(p.get_host_api_count()):
                info = p.get_host_api_info_by_index(i)
                if "wasapi" in info.get("name", "").lower():
                    wasapi_host_api_index = i
                    break
        except Exception as e:
            logger.warning(f"Could not enumerate host APIs: {e}")

        if wasapi_host_api_index is None:
            logger.warning("WASAPI host API not found")
            return None

        # Find the default output device for this host API
        try:
            wasapi_info = p.get_host_api_info_by_index(wasapi_host_api_index)
            default_out_idx = wasapi_info.get("defaultOutputDevice", -1)
            if default_out_idx >= 0:
                default_speakers = p.get_device_info_by_index(default_out_idx)
                if default_speakers.get("isLoopbackDevice", False):
                    return default_speakers
        except Exception as e:
            logger.warning(f"Could not get default WASAPI output: {e}")

        # Fallback: scan all devices for any loopback device
        for i in range(p.get_device_count()):
            try:
                dev = p.get_device_info_by_index(i)
                if dev.get("isLoopbackDevice", False):
                    if self._device_id is None or dev.get("name") == self._device_id:
                        return dev
            except Exception:
                continue

        return None

    def _capture_loop(self) -> None:
        """Main capture loop running in separate thread."""
        try:
            import pyaudiowpatch as pyaudio
        except ImportError:
            logger.error("pyaudiowpatch not installed, loopback capture unavailable")
            return

        self._pyaudio = pyaudio.PyAudio()
        device = self._find_loopback_device(self._pyaudio)

        if device is None:
            logger.error("No WASAPI loopback device found")
            self._pyaudio.terminate()
            self._pyaudio = None
            return

        device_sample_rate = int(device["defaultSampleRate"])
        device_channels = int(device["maxInputChannels"])

        frames_per_buffer = int(device_sample_rate * self._chunk_duration_ms / 1000)

        logger.info(
            f"Opening loopback: {device['name']} @ {device_sample_rate}Hz, "
            f"{device_channels}ch"
        )

        try:
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=device_channels,
                rate=device_sample_rate,
                input=True,
                input_device_index=device["index"],
                frames_per_buffer=frames_per_buffer,
            )

            while self._running:
                try:
                    data = self._stream.read(frames_per_buffer, exception_on_overflow=False)
                    if data and self._running:
                        processed = self._process_audio(
                            data, device_sample_rate, device_channels
                        )
                        if processed:
                            self._on_audio(processed, "meeting")
                except Exception as e:
                    if self._running:
                        logger.warning(f"Loopback read error: {e}")

        except Exception as e:
            logger.error(f"Failed to open loopback stream: {e}")
        finally:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
            if self._pyaudio:
                self._pyaudio.terminate()
                self._pyaudio = None

    def _process_audio(
        self, data: bytes, source_rate: int, source_channels: int
    ) -> Optional[bytes]:
        """Resample and convert to target format if needed."""
        import numpy as np

        samples = np.frombuffer(data, dtype=np.int16)

        if source_channels > self._channels:
            samples = samples.reshape(-1, source_channels)
            samples = samples[:, 0]

        if source_rate != self._sample_rate:
            ratio = self._sample_rate / source_rate
            new_length = int(len(samples) * ratio)
            indices = np.linspace(0, len(samples) - 1, new_length).astype(int)
            samples = samples[indices]

        return samples.astype(np.int16).tobytes()

    def start(self) -> None:
        """Start loopback capture."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._thread.start()
            logger.info("Loopback capture started")

    def stop(self) -> None:
        """Stop loopback capture."""
        with self._lock:
            if not self._running:
                return
            self._running = False

        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("Loopback capture stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    @staticmethod
    def list_loopback_devices() -> list[dict]:
        """List available WASAPI loopback devices."""
        try:
            import pyaudiowpatch as pyaudio
        except ImportError:
            return []

        devices = []
        p = pyaudio.PyAudio()
        try:
            for i in range(p.get_device_count()):
                dev = p.get_device_info_by_index(i)
                if dev.get("isLoopbackDevice", False):
                    devices.append({
                        "id": dev["name"],
                        "name": dev["name"],
                        "sample_rate": int(dev["defaultSampleRate"]),
                        "channels": int(dev["maxInputChannels"]),
                    })
        finally:
            p.terminate()
        return devices
