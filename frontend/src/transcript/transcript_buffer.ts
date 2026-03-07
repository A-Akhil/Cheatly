// Client-side transcript buffer that stores recent transcript segments.
//
// Responsibilities:
// - Receive transcript segment strings from websocket_client.ts
// - Maintain an ordered array of recent segments in memory
// - Trim old segments beyond a configured display history limit
// - Expose a reactive state or event emitter for transcript_view.tsx to consume
// - Provide clear() to reset on session change
