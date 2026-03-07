// Controls all desktop window behaviors for the Cheatly overlay.
//
// Responsibilities:
// - Set the window as always-on-top using Tauri window API
// - Configure the window as frameless with a transparent background
// - Apply platform-specific screen capture exclusion:
//     - Windows: call SetWindowDisplayAffinity with WDA_EXCLUDEFROMCAPTURE
//       so the window does not appear in OBS, Zoom, or any screen recording
//     - macOS: set sharingType to NSWindowSharingNone so the window is
//       excluded from screen sharing in all applications
//     - Linux: apply X11 _NET_WM_BYPASS_COMPOSITOR and compositor hints
//       to request exclusion from screen capture where the compositor supports it
// - Restore window position from persisted settings on launch
// - Expose set_position(x, y) and set_opacity(value) as Tauri commands
//   callable from the frontend via invoke()
