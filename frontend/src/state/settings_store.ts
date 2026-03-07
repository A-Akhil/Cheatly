// Zustand or React context store for user settings state.
//
// Responsibilities:
// - Hold all user preferences as reactive state (opacity, model, audio device, etc.)
// - Expose updateSettings(partial: Partial<Settings>) action
// - Initialize state from the backend on app startup via api_client.ts getSettings()
// - Persist setting changes back to the backend via api_client.ts postSettings()
// - Used by settings_panel.tsx and opacity_controller.ts
