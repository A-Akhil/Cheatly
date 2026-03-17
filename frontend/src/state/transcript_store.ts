import { useSyncExternalStore } from "react";

type TranscriptState = {
	segments: string[];
};

let state: TranscriptState = {
	segments: []
};

const listeners = new Set<() => void>();

function emit(): void {
	for (const listener of listeners) {
		listener();
	}
}

export const transcriptStore = {
	appendSegment(text: string): void {
		const cleaned = text.trim();
		if (!cleaned) {
			return;
		}
		state = {
			...state,
			segments: [...state.segments.slice(-49), cleaned]
		};
		emit();
	},

	clearTranscript(): void {
		state = {
			...state,
			segments: []
		};
		emit();
	},

	getSnapshot(): TranscriptState {
		return state;
	},

	subscribe(listener: () => void): () => void {
		listeners.add(listener);
		return () => listeners.delete(listener);
	}
};

export function useTranscriptStore(): TranscriptState {
	return useSyncExternalStore(transcriptStore.subscribe, transcriptStore.getSnapshot, transcriptStore.getSnapshot);
}
