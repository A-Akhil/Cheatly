# Cheatly

Real-time AI assistant for meetings and interviews. Captures audio from your microphone and meeting applications, transcribes speech in real-time, and provides contextual suggestions via an overlay that is invisible to screen capture.

## Features

- Real-time speech-to-text via faster-whisper
- Two-stage suggestion trigger (Draft/Final) with configurable presets
- LiteLLM integration for wide LLM provider support (OpenAI, Anthropic, Ollama, etc.)
- WASAPI loopback capture for meeting audio (Windows)
- RAG-powered context from uploaded documents
- Screen capture exclusion (overlay hidden from recordings/screen share)
- Compact overlay UI with transcript display and manual input

## Architecture

```
[Microphone] ----\
                  +--> [Audio Source Manager] --> [Whisper STT] --> [Transcript Buffer]
[Meeting Audio] -/                                                         |
                                                                           v
                                                              [Trigger Policy] --> [Suggestion Engine]
                                                                                          |
                                                                                          v
                                                               [WebSocket] <-- [LiteLLM Provider]
                                                                   |
                                                                   v
                                                            [Avalonia Overlay]
```

## Repository Structure

```
cheatly/
  backend/           # Python FastAPI backend
    api/             # REST + WebSocket endpoints
    audio/           # Microphone + loopback capture
    llm/             # LiteLLM provider
    pipeline/        # Trigger policy, suggestion engine
    stt/             # Whisper transcription
    context/         # RAG knowledge base
    tests/           # pytest test suite
  avalonia/          # C# Avalonia desktop client
    Cheatly.Avalonia/
      Services/      # Backend client, WebSocket client
      ViewModels/    # Overlay ViewModel
      Models/        # Data models
  config/            # Configuration files
  models/            # Local model storage (whisper, llm)
  docs/              # Documentation
```

## Quick Start

### Prerequisites

- Python 3.11+
- .NET 8 SDK
- Windows 10 1903+ (for capture exclusion)

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8765
```

### Avalonia Client Setup

```bash
cd avalonia/Cheatly.Avalonia
dotnet run
```

### Running Tests

```bash
cd backend
pytest tests/
```

## Configuration

### LLM Provider

Edit `backend/config/default_config.yaml`:

```yaml
model_provider:
  model: "gpt-4"              # Primary model (LiteLLM format)
  fallback_model: "ollama/llama3"  # Fallback model
  api_base: null              # Optional API base URL
```

Supported model formats:
- OpenAI: `gpt-4`, `gpt-3.5-turbo`
- Anthropic: `claude-3-opus`, `claude-3-sonnet`
- Ollama: `ollama/llama3`, `ollama/mistral`
- Google: `gemini/gemini-pro`

### Trigger Presets

| Preset | Prefetch | Final | Use Case |
|--------|----------|-------|----------|
| Fast | 350ms | 700ms | Quick responses, may be less accurate |
| Balanced | 500ms | 950ms | Default, good balance |
| Accurate | 700ms | 1250ms | More context, slower response |

### Environment Variables

Create `backend/.env`:

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

1. Launch the backend server
2. Launch the Avalonia client
3. Click "Connect" in the Settings window
4. Configure your LLM model and trigger preset
5. Optionally upload RAG documents for context
6. Click "Start Session" to open the overlay
7. The overlay will display suggestions as you speak

### Overlay Controls

- Drag the header to reposition
- Type in the text box to add context
- Click "Send" to force a suggestion refresh
- Click "X" to end the session

## Screen Capture Exclusion

The overlay uses `SetWindowDisplayAffinity` with `WDA_EXCLUDEFROMCAPTURE` to hide from:
- OBS Studio
- Zoom screen share
- Microsoft Teams screen share
- Windows Game Bar recording
- Most other capture tools

Requires Windows 10 version 1903 (build 18362) or later.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/models` | GET | Current LLM configuration |
| `/settings` | POST | Update model/trigger settings |
| `/transcription/start` | POST | Start audio capture |
| `/transcription/stop` | POST | Stop audio capture |
| `/transcript/ingest` | POST | Manual transcript input |
| `/rag/documents` | GET | List RAG documents |
| `/rag/documents/text` | POST | Add text document |
| `/audio/devices` | GET | List audio devices |
| `/ws/suggestions` | WebSocket | Live suggestion stream |

## License

MIT
