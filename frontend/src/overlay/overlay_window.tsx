// Main overlay window component — the root floating UI element.
//
// Responsibilities:
// - Render the top-level frameless, always-on-top overlay window
// - Contain overlay_container.tsx as its primary child
// - Apply transparent background and no window chrome styling
// - Initialize drag behavior by wiring drag_manager.ts to mouse events
// - Initialize opacity by reading the configured value from settings_store.ts
// - Subscribe to connection state from services/connection_manager.ts
// - Show a minimal disconnected indicator if the backend WebSocket drops
