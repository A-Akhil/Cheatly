// Handles platform-specific permission requests required by the application.
//
// Responsibilities:
// - On macOS: request microphone access using AVFoundation authorization API
//   before the audio capture begins, and show the system permission dialog
// - On Windows: verify microphone access is granted in Windows Privacy settings
//   and surface an error to the user if it is blocked
// - On Linux: check if the user has access to the audio input device via
//   PulseAudio or ALSA and surface a warning if access is denied
// - Expose a check_permissions() function called by main.rs at startup
// - Return a permissions status struct indicating which permissions are granted
