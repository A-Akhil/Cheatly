// Zustand or React context store for AI suggestion state.
//
// Responsibilities:
// - Hold the current list of AI-generated suggestion strings as reactive state
// - Expose addSuggestion(text: string) called by suggestion_stream.ts
// - Expose clearSuggestions() called when a new context window begins
// - Track loading state (true while the backend is generating suggestions)
// - Used by suggestion_panel.tsx to render the suggestion list
