// React component that renders the AI suggestion panel.
//
// Responsibilities:
// - Subscribe to suggestion updates from suggestion_store.ts
// - Render suggestions as a vertical list of bullet points
// - Animate new suggestions sliding in as they stream from the backend
// - Allow the user to click a suggestion to copy it to the clipboard
// - Show a loading indicator while a new suggestion is being generated
// - Clear and replace suggestions when a new transcript context arrives
