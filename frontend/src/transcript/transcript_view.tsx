// React component that displays the live speech transcription.
//
// Responsibilities:
// - Subscribe to transcript updates from transcript_store.ts
// - Render the current spoken sentence in a scrollable text area
// - Auto-scroll to the latest transcript segment as new text arrives
// - Show a visual pulse or indicator while audio is actively being captured
// - Fade out older transcript segments to emphasize the most recent text
// - Keep the component compact to minimize overlay footprint
