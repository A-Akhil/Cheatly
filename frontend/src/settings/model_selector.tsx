// UI component for selecting the active LLM model and provider.
//
// Responsibilities:
// - Display a dropdown of available Ollama models fetched from GET /models
// - Display a field for entering an API model identifier for LiteLLM
// - Toggle between local (Ollama) and API provider mode
// - Show API key input field when API provider is selected
// - Emit the selected model and provider values to settings_panel.tsx
