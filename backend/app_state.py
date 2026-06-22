from __future__ import annotations

import asyncio
import logging
import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from backend.api.websocket import WebSocketHub
from backend.audio.audio_buffer import AudioBuffer
from backend.audio.microphone import Microphone
from backend.audio.stream_manager import StreamManager
from backend.audio.source_manager import AudioSourceManager, AudioSourceConfig
from backend.config.config_loader import ConfigLoader
from backend.context.knowledge_base import KnowledgeBase
from backend.context.memory_store import MemoryStore
from backend.context.session_manager import SessionManager
from backend.context.transcript_history import TranscriptHistory
from backend.llm.provider_manager import ProviderManager
from backend.models.audio_chunk import AudioChunk
from backend.pipeline.context_manager import ConversationContextManager
from backend.pipeline.suggestion_engine import SuggestionEngine
from backend.pipeline.transcription_pipeline import TranscriptionPipeline
from backend.pipeline.trigger_policy import TriggerPolicy, PRESETS
from backend.stt.model_loader import ModelLoader
from backend.stt.streaming_transcriber import StreamingTranscriber
from backend.stt.transcript_buffer import TranscriptBuffer
from backend.stt.whisper_engine import WhisperEngine

logger = logging.getLogger(__name__)


@dataclass
class BackendState:
    config_loader: ConfigLoader
    config: dict[str, Any]
    ws_hub: WebSocketHub
    memory_store: MemoryStore
    session_manager: SessionManager
    transcript_history: TranscriptHistory
    conversation_context: ConversationContextManager
    kb: KnowledgeBase
    provider_manager: ProviderManager
    transcription_pipeline: TranscriptionPipeline
    suggestion_engine: SuggestionEngine
    trigger_policy: TriggerPolicy
    audio_buffer: AudioBuffer
    transcript_buffer: TranscriptBuffer
    stream_manager: StreamManager
    streaming_transcriber: StreamingTranscriber
    audio_source_manager: Optional[AudioSourceManager] = field(default=None)
    _event_loop: Optional[asyncio.AbstractEventLoop] = field(default=None)
    stt_available: bool = field(default=True)
    stt_preload_ready: Optional[bool] = field(default=None)

    @classmethod
    def build(cls, config_loader: ConfigLoader) -> "BackendState":
        config = config_loader.get_all()
        rag_cfg = config.get("rag", {})
        trigger_cfg = config.get("trigger", {})

        ws_hub = WebSocketHub()
        memory_store = MemoryStore()
        session_manager = SessionManager()
        transcript_history = TranscriptHistory()
        conversation_context = ConversationContextManager(max_items=20)
        kb = KnowledgeBase(
            sqlite_path=rag_cfg.get("sqlite_path", "./backend/context/rag_store.db"),
            chunk_size=int(rag_cfg.get("chunk_size", 700)),
            chunk_overlap=int(rag_cfg.get("chunk_overlap", 120)),
        )

        provider_manager = ProviderManager(config)
        transcription_pipeline = TranscriptionPipeline(transcript_history)
        suggestion_engine = SuggestionEngine(
            provider_manager=provider_manager,
            kb=kb,
            context_manager=conversation_context,
            top_k=int(rag_cfg.get("top_k", 5)),
        )

        preset_name = trigger_cfg.get("preset", "balanced")
        preset = PRESETS.get(preset_name, PRESETS["balanced"])
        trigger_policy = TriggerPolicy(preset)

        audio_cfg = config.get("audio", {})
        stt_cfg = config.get("speech_recognition", {})
        logging_cfg = config.get("logging", {})

        audio_buffer = AudioBuffer(max_chunks=96)
        transcript_buffer = TranscriptBuffer(max_items=256)
        microphone = Microphone(
            audio_buffer=audio_buffer,
            sample_rate=int(audio_cfg.get("sample_rate", 16000)),
            channels=int(audio_cfg.get("channels", 1)),
            chunk_duration_ms=int(stt_cfg.get("chunk_duration_ms", 800)),
            device_index=audio_cfg.get("device_index"),
        )
        stream_manager = StreamManager(microphone=microphone, audio_buffer=audio_buffer)

        stt_enabled = bool(stt_cfg.get("enabled", False))
        stt_device = str(stt_cfg.get("device", "cpu"))
        stt_compute_type = str(stt_cfg.get("compute_type", "int8"))
        stt_cpu_threads = int(stt_cfg.get("cpu_threads", 1))
        stt_num_workers = int(stt_cfg.get("num_workers", 1))
        stt_use_mkl = bool(stt_cfg.get("use_mkl", False))
        model_cache_dir = str(stt_cfg.get("model_cache_dir", "./models/whisper"))
        if platform.system().lower() == "windows":
            configured_path = Path(model_cache_dir)
            if not configured_path.is_absolute():
                local_appdata = os.getenv("LOCALAPPDATA")
                if local_appdata:
                    model_cache_dir = str(Path(local_appdata) / "Cheatly" / "whisper")
            logger.info(f"[stt] using whisper cache dir: {model_cache_dir}")
        isolate_process = bool(stt_cfg.get("isolate_process", platform.system().lower() == "windows"))
        if platform.system().lower() == "windows" and stt_compute_type.lower() == "int8":
            logger.warning("Overriding STT compute_type int8 -> float32 on Windows for stability")
            stt_compute_type = "float32"
        model_loader = ModelLoader(
            model_size=str(stt_cfg.get("model_size", "base")),
            device=stt_device,
            compute_type=stt_compute_type,
            download_root=model_cache_dir,
            cpu_threads=stt_cpu_threads,
            num_workers=stt_num_workers,
        )
        if not stt_enabled:
            logger.info("Speech recognition disabled via config; skipping Whisper model load")
            whisper_engine = WhisperEngine(
                model=None,
                sample_rate=int(audio_cfg.get("sample_rate", 16000)),
                model_factory=None,
            )
        else:
            logger.info(
                f"Speech recognition enabled; Whisper load deferred until first transcription "
                f"(model={stt_cfg.get('model_size', 'base')}, device={stt_device}, "
                f"compute_type={stt_compute_type}, isolate_process={isolate_process}, cache_dir={model_cache_dir})"
            )
            whisper_engine = WhisperEngine(
                model=None,
                sample_rate=int(audio_cfg.get("sample_rate", 16000)),
                model_factory=model_loader.load_whisper,
                worker_config={
                    "model_size": str(stt_cfg.get("model_size", "base")),
                    "device": stt_device,
                    "compute_type": stt_compute_type,
                    "fallback_model_sizes": stt_cfg.get("fallback_model_sizes", ["small", "tiny", "tiny.en"]),
                    "fallback_compute_types": stt_cfg.get("fallback_compute_types", ["int8", "int8_float32", "float32"]),
                    "cpu_threads": stt_cpu_threads,
                    "num_workers": stt_num_workers,
                    "use_mkl": stt_use_mkl,
                    "language": str(stt_cfg.get("language", "en")),
                    "model_cache_dir": model_cache_dir,
                    "worker_fault_file": str(logging_cfg.get("worker_fault_file_path", "./backend/logging/whisper_worker_fault.log")),
                },
                isolate_process=isolate_process,
            )

        def on_transcript(text: str) -> None:
            transcript_history.append(text)

        streaming_transcriber = StreamingTranscriber(
            audio_buffer=audio_buffer,
            transcript_buffer=transcript_buffer,
            whisper=whisper_engine,
            on_transcript=on_transcript,
            # on_segment is wired after construction via set_segment_callback()
        )

        return cls(
            config_loader=config_loader,
            config=config,
            ws_hub=ws_hub,
            memory_store=memory_store,
            session_manager=session_manager,
            transcript_history=transcript_history,
            conversation_context=conversation_context,
            kb=kb,
            provider_manager=provider_manager,
            transcription_pipeline=transcription_pipeline,
            suggestion_engine=suggestion_engine,
            trigger_policy=trigger_policy,
            audio_buffer=audio_buffer,
            transcript_buffer=transcript_buffer,
            stream_manager=stream_manager,
            streaming_transcriber=streaming_transcriber,
        )

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._event_loop = loop

    def reset_session(self) -> None:
        self.session_manager.reset()
        self.memory_store.clear()
        self.transcript_history.clear()
        self.conversation_context.clear()
        self.trigger_policy.reset()
        self.suggestion_engine.clear_turn_outputs()

    def reload_config(self, new_config: dict[str, Any]) -> None:
        self.config = new_config
        self.provider_manager.reload(new_config)
        preset_name = self.config.get("trigger", {}).get("preset", "balanced")
        self.trigger_policy.reload(str(preset_name))

    def start_transcription(self) -> None:
        logger.info("[stt] start_transcription: begin")
        logger.info(f"[stt] stream_manager_running_before={self.stream_manager.is_running}")
        logger.info(f"[stt] transcriber_running_before={self.streaming_transcriber.is_running}")
        stt_cfg = self.config.get("speech_recognition", {})
        try:
            if bool(stt_cfg.get("enabled", False)):
                if not self.streaming_transcriber.whisper.is_available:
                    logger.info("[stt] start_transcription: whisper not ready, retrying preload")
                    ready = self.streaming_transcriber.whisper.preload()
                    self.stt_available = bool(ready)
                    self.stt_preload_ready = bool(ready)
                if not self.streaming_transcriber.whisper.is_available:
                    self.stt_available = False
                    raise RuntimeError("Speech recognition is unavailable (whisper worker not ready)")

            # Wire the segment callback so transcripts flow to the trigger policy + LLM
            self.streaming_transcriber.on_segment = self.process_segment
            # Wire transcript broadcast so the overlay shows live captions
            self.streaming_transcriber.on_transcript = self._on_transcript_with_broadcast

            # Start mic capture via stream_manager
            logger.info("[stt] start_transcription: starting stream_manager (mic)")
            self.stream_manager.start()
            logger.info(f"[stt] start_transcription: stream_manager_running_after={self.stream_manager.is_running}")

            # Also start loopback (system/meeting audio) capture
            logger.info("[stt] start_transcription: starting loopback capture")
            self.start_unified_capture(enable_mic=False, enable_loopback=True)

            logger.info("[stt] start_transcription: starting streaming_transcriber")
            self.streaming_transcriber.start()
            logger.info(f"[stt] start_transcription: transcriber_running_after={self.streaming_transcriber.is_running}")
            self.stt_available = True
            logger.info("[stt] start_transcription: complete")
        except Exception:
            logger.exception("[stt] start_transcription: failed")
            raise

    def stop_transcription(self) -> None:
        logger.info("[stt] stop_transcription: begin")
        try:
            self.streaming_transcriber.stop()
            self.stream_manager.stop()
            self.stop_unified_capture()  # Stop loopback too
            logger.info("[stt] stop_transcription: complete")
        except Exception:
            logger.exception("[stt] stop_transcription: failed")
            raise

    def preload_speech_model(self) -> bool:
        stt_cfg = self.config.get("speech_recognition", {})
        if not bool(stt_cfg.get("enabled", False)):
            logger.info("[stt] preload skipped: speech_recognition.enabled=false")
            self.stt_available = True
            self.stt_preload_ready = True
            return True

        logger.info("[stt] preload start")
        ready = self.streaming_transcriber.whisper.preload()
        self.stt_available = bool(ready)
        self.stt_preload_ready = bool(ready)
        logger.info(f"[stt] preload done ready={ready}")
        return ready

    def shutdown(self) -> None:
        self.stop_transcription()
        try:
            self.streaming_transcriber.whisper.close()
        except Exception:
            logger.exception("[stt] whisper close failed during shutdown")

    def _on_audio_chunk(self, chunk: AudioChunk) -> None:
        self.audio_buffer.push(chunk.data)

    def _on_transcript_with_broadcast(self, text: str) -> None:
        """Called for every transcript — logs it and broadcasts to WebSocket for live captions."""
        logger.info(f"[stt] transcript: {repr(text)}")
        if self._event_loop is not None:
            asyncio.run_coroutine_threadsafe(
                self.ws_hub.broadcast({"type": "transcript", "payload": {"text": text}}),
                self._event_loop,
            )

    async def _process_segment_async(self, segment) -> None:
        trigger_result = self.trigger_policy.feed(segment)
        if trigger_result is None:
            return

        # TriggerEvent is an Enum — use .value to get the string "final"/"prefetch"
        mode = trigger_result.value.lower()
        text = segment.text
        logger.info(f"[trigger] fired mode={mode} text={repr(text[:60])}")

        # Run the blocking LLM call in a thread so we don't freeze the event loop
        result = await asyncio.to_thread(
            self.suggestion_engine.generate_suggestions,
            text,
            turn_id=segment.turn_id,
            mode=mode,
        )
        logger.info(f"[trigger] suggestions ready mode={mode} count={len(result.get('suggestions', result.get('output', [])))}")

        await self.ws_hub.broadcast({
            "type": "suggestions",
            "payload": {
                "output": result.get("suggestions", result.get("output", [])),
                "turn_id": segment.turn_id,
                "mode": mode,
                "revision": segment.revision,
            }
        })

    def process_segment(self, segment) -> None:
        if self._event_loop is not None:
            asyncio.run_coroutine_threadsafe(
                self._process_segment_async(segment),
                self._event_loop
            )

    def start_unified_capture(self, enable_mic: bool = True, enable_loopback: bool = True) -> None:
        """Start audio source manager for mic and/or loopback capture.
        When called from start_transcription, we only start loopback here
        (mic is handled by stream_manager separately)."""
        if self.audio_source_manager is not None:
            logger.info("[audio] unified capture already running, skipping")
            return

        audio_cfg = self.config.get("audio", {})

        config = AudioSourceConfig(
            enable_mic=enable_mic,
            enable_loopback=enable_loopback,
            sample_rate=int(audio_cfg.get("sample_rate", 16000)),
            channels=int(audio_cfg.get("channels", 1)),
            chunk_duration_ms=100,
        )

        self.audio_source_manager = AudioSourceManager(
            config=config,
            on_audio_chunk=self._on_audio_chunk,
        )
        self.audio_source_manager.start()

    def stop_unified_capture(self) -> None:
        if self.audio_source_manager:
            self.audio_source_manager.stop()
            self.audio_source_manager = None
