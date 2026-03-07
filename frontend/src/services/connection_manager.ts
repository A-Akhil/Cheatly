// Manages the overall connection lifecycle between the frontend and backend.
//
// Responsibilities:
// - Coordinate WebSocket and HTTP connection initialization on app start
// - Track combined connection health (both WebSocket and REST reachability)
// - Expose a global connection status used by overlay_window.tsx
// - Trigger reconnection attempts when the backend becomes unreachable
// - Notify the UI when the backend has fully started and is ready to receive data
