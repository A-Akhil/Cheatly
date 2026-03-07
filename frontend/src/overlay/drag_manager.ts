// Enables drag-to-reposition behavior for the overlay window.
//
// Responsibilities:
// - Attach mousedown, mousemove, and mouseup event listeners to the drag handle
// - Calculate delta movement and update the window position via Tauri window API
// - Persist the final window position to settings_store.ts after drag ends
// - Prevent text selection during drag operations
// - Expose attach(element) and detach() methods for overlay_window.tsx
