// Handles the streaming reception of suggestion tokens from the backend.
//
// Responsibilities:
// - Receive partial suggestion text from websocket_client.ts as tokens stream in
// - Accumulate tokens into complete suggestion strings
// - Push completed suggestions to suggestion_store.ts
// - Detect end-of-stream markers to finalize a suggestion entry
// - Handle stream interruptions and reset partial state cleanly
