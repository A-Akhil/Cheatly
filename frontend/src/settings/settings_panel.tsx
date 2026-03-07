// Root settings panel component that contains all settings sections.
//
// Responsibilities:
// - Render a modal or slide-in panel accessible from the overlay UI
// - Compose model_selector.tsx, audio_settings.tsx, and ui_preferences.tsx
// - Read current settings from settings_store.ts as initial values
// - Collect changed values and submit them via api_client.ts POST /settings
// - Show save confirmation or error feedback after submission
// - Provide a close button that returns to the main overlay view
