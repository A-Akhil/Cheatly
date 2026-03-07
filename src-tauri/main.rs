// Tauri application entry point.
//
// Responsibilities:
// - Initialize the Tauri application builder
// - Register all Tauri commands and event handlers
// - Invoke backend_launcher to spawn the Python backend process on startup
// - Invoke window_manager to configure the overlay window properties
// - Invoke permissions to request microphone access on macOS
// - Keep the Tauri event loop running until the user closes the application
// - Cleanly terminate the backend process when the application exits
