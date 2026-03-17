from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.api.websocket import WebSocketHub
from backend.audio.audio_buffer import AudioBuffer
from backend.audio.microphone import Microphone
from backend.audio.stream_manager import StreamManager
from backend.config.config_loader import ConfigLoader
from backend.context.knowledge_base import KnowledgeBase
from backend.context.memory_store import MemoryStore
from backend.context.session_manager import SessionManager
from backend.context.transcript_history import TranscriptHistory
from backend.llm.provider_manager import ProviderManager
from backend.pipeline.context_manager import ConversationContextManager
from backend.pipeline.suggestion_engine import SuggestionEngine
from backend.pipeline.transcription_pipeline import TranscriptionPipeline
from backend.stt.model_loader import ModelLoader
from backend.stt.streaming_transcriber import StreamingTranscriber
from backend.stt.transcript_buffer import TranscriptBuffer
from backend.stt.whisper_engine import WhisperEngine


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
    audio_buffer: AudioBuffer
    transcript_buffer: TranscriptBuffer
    stream_manager: StreamManager
    streaming_transcriber: StreamingTranscriber

    @classmethod
    def build(cls, config_loader: ConfigLoader) -> "BackendState":
        config = config_loader.get_all()
        rag_cfg = config.get("rag", {})

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

        audio_cfg = config.get("audio", {})
        stt_cfg = config.get("speech_recognition", {})

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

        model_loader = ModelLoader(model_size=str(stt_cfg.get("model_size", "base")))
        whisper_engine = WhisperEngine(model_loader.load_whisper(), sample_rate=int(audio_cfg.get("sample_rate", 16000)))

        def on_transcript(text: str) -> None:
            transcript_history.append(text)

        streaming_transcriber = StreamingTranscriber(
            audio_buffer=audio_buffer,
            transcript_buffer=transcript_buffer,
            whisper=whisper_engine,
            on_transcript=on_transcript,
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
            audio_buffer=audio_buffer,
            transcript_buffer=transcript_buffer,
            stream_manager=stream_manager,
            streaming_transcriber=streaming_transcriber,
        )

    def reset_session(self) -> None:
        self.session_manager.reset()
        self.memory_store.clear()
        self.transcript_history.clear()
        self.conversation_context.clear()

    def reload_config(self, new_config: dict[str, Any]) -> None:
        self.config = new_config
        self.provider_manager.reload(new_config)

    def start_transcription(self) -> None:
        self.stream_manager.start()
        self.streaming_transcriber.start()

    def stop_transcription(self) -> None:
        self.streaming_transcriber.stop()
        self.stream_manager.stop()
