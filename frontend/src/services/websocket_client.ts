// WebSocket client that maintains the real-time connection to the backend.
//
// Responsibilities:
// - Open a WebSocket connection to the backend server on startup
// - Dispatch incoming messages to transcript_buffer.ts or suggestion_stream.ts
//   based on the message type field
// - Automatically reconnect with exponential backoff on connection loss
// - Notify connection_manager.ts of connect and disconnect events
// - Provide a send(message) method for future bidirectional communication
// - Expose connection state (connected, connecting, disconnected) as a reactive value
