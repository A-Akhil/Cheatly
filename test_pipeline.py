"""
Cheatly End-to-End Pipeline Diagnostic
Run from project root:  python test_pipeline.py
"""
import sys
import os
import time
import asyncio
import struct
import math

# Force UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(__file__))

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"
INFO = "[INFO]"


def hdr(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ── 1. WASAPI / pyaudiowpatch ─────────────────────────────────────
hdr("1. WASAPI Loopback (pyaudiowpatch)")
try:
    import pyaudiowpatch as pyaudio
    p = pyaudio.PyAudio()

    # List ALL host APIs
    host_api_count = p.get_host_api_count()
    print(f"  {INFO} Host API count: {host_api_count}")
    wasapi_index = None
    for i in range(host_api_count):
        info = p.get_host_api_info_by_index(i)
        name = info.get("name", "")
        print(f"       [{i}] {name}")
        if "wasapi" in name.lower() or "WASAPI" in name:
            wasapi_index = i

    if wasapi_index is None:
        print(f"  {FAIL} WASAPI host API not found in any slot!")
        print(f"  {WARN} This is why loopback fails. Check Windows audio drivers.")
    else:
        print(f"  {PASS} WASAPI found at index {wasapi_index}")

    # List loopback devices
    loopback_devices = []
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev.get("isLoopbackDevice", False):
            loopback_devices.append(dev)
            print(f"  {PASS} Loopback device: [{i}] {dev['name']} @ {int(dev['defaultSampleRate'])}Hz")

    if not loopback_devices:
        print(f"  {FAIL} No loopback devices found.")
        print(f"  {WARN} Try: go to Sound Settings → your output device → Properties → enable 'Stereo Mix' or check if WASAPI drivers are installed")
    else:
        print(f"  {PASS} {len(loopback_devices)} loopback device(s) available")

    # Try via get_host_api_info_by_type
    try:
        wasapi_info = p.get_host_api_info_by_type(p.paWASAPI)
        default_out_idx = wasapi_info["defaultOutputDevice"]
        default_out = p.get_device_info_by_index(default_out_idx)
        print(f"  {PASS} Default WASAPI output: {default_out['name']}")
        print(f"       isLoopbackDevice = {default_out.get('isLoopbackDevice', False)}")
    except Exception as e:
        print(f"  {FAIL} get_host_api_info_by_type(paWASAPI) failed: {e}")
        print(f"  {WARN} This is the exact line that crashes in loopback.py line 49!")

    p.terminate()

except ImportError:
    print(f"  {FAIL} pyaudiowpatch not installed")
except Exception as e:
    print(f"  {FAIL} pyaudiowpatch error: {e}")


# ── 2. Mic devices (sounddevice) ──────────────────────────────────
hdr("2. Microphone Devices (sounddevice)")
try:
    import sounddevice as sd
    devices = sd.query_devices()
    mic_count = 0
    for i, d in enumerate(devices):
        if d["max_input_channels"] > 0:
            mic_count += 1
            marker = "(default)" if i == sd.default.device[0] else ""
            print(f"  {PASS} Mic [{i}] {d['name']} {marker}")
    if mic_count == 0:
        print(f"  {FAIL} No microphone devices found!")
    else:
        print(f"\n  {PASS} {mic_count} mic(s) found")
except Exception as e:
    print(f"  {FAIL} sounddevice error: {e}")


# ── 3. AudioBuffer ────────────────────────────────────────────────
hdr("3. AudioBuffer push/pop")
try:
    from backend.audio.audio_buffer import AudioBuffer
    buf = AudioBuffer(max_chunks=10)
    buf.push(b"\x00\x01" * 100)
    buf.push(b"\x02\x03" * 100)
    chunks = buf.pop_all()
    assert len(chunks) == 2, f"Expected 2 chunks, got {len(chunks)}"
    assert buf.pop_all() == [], "Buffer should be empty after pop_all"
    print(f"  {PASS} AudioBuffer: push/pop_all works")
except Exception as e:
    print(f"  {FAIL} AudioBuffer: {e}")


# ── 4. TranscriptBuffer + TurnSegment ────────────────────────────
hdr("4. TranscriptBuffer + TurnSegment")
try:
    from backend.stt.transcript_buffer import TranscriptBuffer
    tb = TranscriptBuffer()
    seg1 = tb.append("Hello this is a test")
    assert seg1 is not None, "append returned None"
    seg2 = tb.append("How are you doing today")
    assert seg2 is not None
    assert seg1.turn_id == seg2.turn_id, "Same turn expected within 1200ms"
    all_texts = tb.get_all()
    assert "Hello this is a test" in all_texts
    print(f"  {PASS} TranscriptBuffer: append, same-turn grouping work")
    seg_latest = tb.get_latest_segment()
    assert seg_latest.text == "How are you doing today"
    print(f"  {PASS} TranscriptBuffer: get_latest_segment works")
except Exception as e:
    print(f"  {FAIL} TranscriptBuffer: {e}")


# ── 5. TriggerPolicy ─────────────────────────────────────────────
hdr("5. TriggerPolicy")
try:
    from backend.pipeline.trigger_policy import TriggerPolicy, PRESETS, TriggerEvent
    from backend.models.turn_segment import TurnSegment
    import uuid

    policy = TriggerPolicy(PRESETS["fast"])

    def make_seg(text, is_final=False):
        return TurnSegment(
            text=text,
            turn_id=str(uuid.uuid4()),
            revision=0,
            mode="prefetch",
            source="mic",
            timestamp_ms=int(time.time() * 1000),
            is_final=is_final,
        )

    # is_final=True should always fire FINAL
    seg = make_seg("Tell me about yourself and your background please", is_final=True)
    result = policy.feed(seg)
    assert result == TriggerEvent.FINAL, f"Expected FINAL for is_final=True, got {result}"
    print(f"  {PASS} TriggerPolicy: is_final=True → FINAL trigger")

    # Short text should not prefetch (< MIN_TOKENS_FOR_PREFETCH=8)
    policy2 = TriggerPolicy(PRESETS["fast"])
    seg_short = make_seg("hi there")
    result2 = policy2.feed(seg_short)
    assert result2 is None, f"Expected None for short text, got {result2}"
    print(f"  {PASS} TriggerPolicy: short text suppressed (< 8 tokens)")
except Exception as e:
    print(f"  {FAIL} TriggerPolicy: {e}")


# ── 6. PromptBuilder + ResponseParser ────────────────────────────
hdr("6. PromptBuilder + ResponseParser")
try:
    from backend.llm.prompt_builder import PromptBuilder
    from backend.llm.response_parser import ResponseParser

    pb = PromptBuilder()
    prompt = pb.build(
        transcript="Tell me about yourself",
        history_text="Previous context here",
        rag_chunks=[],
    )
    assert len(prompt) > 10, "Prompt is empty"
    print(f"  {PASS} PromptBuilder: generates prompt ({len(prompt)} chars)")

    rp = ResponseParser()
    raw = "- First suggestion\n- Second suggestion\n- Third suggestion"
    bullets = rp.to_bullets(raw)
    assert len(bullets) >= 2, f"Expected >=2 bullets, got {bullets}"
    print(f"  {PASS} ResponseParser: parses {len(bullets)} bullets from response")
except Exception as e:
    print(f"  {FAIL} PromptBuilder/ResponseParser: {e}")


# ── 7. LLM (Ollama tinyllama) ─────────────────────────────────────
hdr("7. LLM via Ollama (tinyllama)")
try:
    from backend.llm.litellm_provider import LiteLLMProvider
    provider = LiteLLMProvider(
        model="ollama/tinyllama",
        api_base="http://127.0.0.1:11434",
        temperature=0.1,
        max_tokens=64,
    )
    t0 = time.time()
    resp = provider.generate("Say 'hello' in one word")
    elapsed = time.time() - t0
    assert len(resp) > 0, "Empty response from LLM"
    print(f"  {PASS} LLM response in {elapsed:.1f}s: {repr(resp[:80])}")
except Exception as e:
    print(f"  {FAIL} LLM call failed: {e}")
    print(f"  {WARN} Is Ollama running? Run: ollama serve")


# ── 8. SuggestionEngine end-to-end ────────────────────────────────
hdr("8. SuggestionEngine (full LLM call)")
try:
    from backend.llm.provider_manager import ProviderManager
    from backend.context.knowledge_base import KnowledgeBase
    from backend.pipeline.context_manager import ConversationContextManager
    from backend.pipeline.suggestion_engine import SuggestionEngine

    cfg = {
        "model_provider": {
            "provider": "ollama",
            "model": "ollama/tinyllama",
            "api_base": "http://127.0.0.1:11434",
            "temperature": 0.1,
            "max_tokens": 64,
        }
    }
    pm = ProviderManager(cfg)
    kb = KnowledgeBase(sqlite_path=":memory:", chunk_size=200, chunk_overlap=20)
    ctx = ConversationContextManager(max_items=5)
    engine = SuggestionEngine(pm, kb, ctx)

    t0 = time.time()
    result = engine.generate_suggestions(
        transcript="Tell me about your experience with Python",
        mode="final",
        turn_id="test-turn-1",
    )
    elapsed = time.time() - t0

    suggestions = result.get("suggestions", result.get("output", []))
    raw = result.get("raw", "")
    print(f"  {PASS} SuggestionEngine responded in {elapsed:.1f}s")
    print(f"       raw[:100]: {repr(raw[:100])}")
    print(f"       suggestions key = {'suggestions' if 'suggestions' in result else 'output'}")
    print(f"       parsed bullets: {suggestions}")
except Exception as e:
    print(f"  {FAIL} SuggestionEngine: {e}")


# ── 9. StreamingTranscriber wiring (on_segment callback) ──────────
hdr("9. StreamingTranscriber on_segment wiring")
try:
    from backend.audio.audio_buffer import AudioBuffer
    from backend.stt.transcript_buffer import TranscriptBuffer
    from backend.stt.whisper_engine import WhisperEngine
    from backend.stt.streaming_transcriber import StreamingTranscriber

    received_segments = []

    def fake_on_segment(seg):
        received_segments.append(seg)

    audio_buf = AudioBuffer()
    tx_buf = TranscriptBuffer()

    # Use a mock whisper engine that returns a fixed transcript
    class FakeWhisper:
        is_available = True
        def transcribe(self, chunk):
            return "this is a test transcript"

    st = StreamingTranscriber(
        audio_buffer=audio_buf,
        transcript_buffer=tx_buf,
        whisper=FakeWhisper(),
        on_segment=fake_on_segment,
    )

    # Push fake audio and process
    audio_buf.push(b"\x00" * 3200)
    st.process_once()

    assert len(received_segments) == 1, f"Expected 1 segment callback, got {len(received_segments)}"
    assert received_segments[0].text == "this is a test transcript"
    print(f"  {PASS} on_segment callback fires with correct TurnSegment")
    print(f"       segment.text = {repr(received_segments[0].text)}")
    print(f"       segment.turn_id = {received_segments[0].turn_id}")
except Exception as e:
    print(f"  {FAIL} StreamingTranscriber on_segment: {e}")
    import traceback; traceback.print_exc()


# ── 10. process_segment → ws_hub broadcast (async) ───────────────
hdr("10. process_segment → WebSocket broadcast (async)")
try:
    from backend.api.websocket import WebSocketHub
    from backend.stt.transcript_buffer import TranscriptBuffer
    from backend.pipeline.trigger_policy import TriggerPolicy, PRESETS
    from backend.pipeline.suggestion_engine import SuggestionEngine
    from backend.llm.provider_manager import ProviderManager
    from backend.context.knowledge_base import KnowledgeBase
    from backend.pipeline.context_manager import ConversationContextManager
    from backend.models.turn_segment import TurnSegment
    import uuid

    broadcast_received = []

    class FakeHub:
        async def broadcast(self, msg):
            broadcast_received.append(msg)

    cfg = {
        "model_provider": {
            "provider": "ollama",
            "model": "ollama/tinyllama",
            "api_base": "http://127.0.0.1:11434",
            "temperature": 0.1,
            "max_tokens": 64,
        }
    }
    pm = ProviderManager(cfg)
    kb = KnowledgeBase(sqlite_path=":memory:", chunk_size=200, chunk_overlap=20)
    ctx = ConversationContextManager(max_items=5)
    engine = SuggestionEngine(pm, kb, ctx)
    policy = TriggerPolicy(PRESETS["fast"])
    hub = FakeHub()

    async def run_test():
        loop = asyncio.get_running_loop()

        # Simulate process_segment logic from app_state
        async def process_segment_async(segment):
            trigger_result = policy.feed(segment)
            if trigger_result is None:
                return "no trigger"

            mode = trigger_result.value.lower()
            result = engine.generate_suggestions(
                segment.text,
                turn_id=segment.turn_id,
                mode=mode,
            )
            await hub.broadcast({
                "type": "suggestions",
                "payload": {
                    "output": result.get("suggestions", result.get("output", [])),
                    "turn_id": segment.turn_id,
                    "mode": mode,
                    "revision": segment.revision,
                }
            })
            return mode

        seg = TurnSegment(
            text="Can you walk me through your experience with distributed systems and microservices",
            turn_id=str(uuid.uuid4()),
            revision=0,
            mode="prefetch",
            source="mic",
            timestamp_ms=int(time.time() * 1000),
            is_final=True,
        )
        triggered = await process_segment_async(seg)
        return triggered

    triggered = asyncio.run(run_test())
    if broadcast_received:
        msg = broadcast_received[0]
        payload = msg.get("payload", {})
        print(f"  {PASS} process_segment triggered: {triggered}")
        print(f"       Broadcast type: {msg.get('type')}")
        print(f"       output bullets: {payload.get('output', [])}")
    else:
        print(f"  {WARN} Trigger returned '{triggered}' → no broadcast fired (segment may be too short or trigger suppressed)")
except Exception as e:
    print(f"  {FAIL} process_segment → broadcast: {e}")
    import traceback; traceback.print_exc()


# ── SUMMARY ───────────────────────────────────────────────────────
hdr("DONE — Review any ✘ or ⚠ above")
