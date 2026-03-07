# Health check endpoint for internal service status monitoring.
#
# Responsibilities:
# - Expose GET /health endpoint returning overall backend status
# - Report status of each subsystem: audio, stt, llm, pipeline
# - Return model loading status and whether whisper is ready
# - Return current active session count
# - Return last known latency metrics for STT and LLM inference
# - Used by Tauri backend_launcher.rs to verify backend is alive after startup
