// Zustand or React context store for transcript state.
//
// Responsibilities:
// - Hold the list of current transcript segments as reactive state
// - Expose appendSegment(text: string) action called by transcript_buffer.ts
// - Expose clearTranscript() action called on session reset
// - Used by transcript_view.tsx to render live transcription
