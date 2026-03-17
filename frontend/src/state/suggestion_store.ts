import { useSyncExternalStore } from "react";

type SuggestionState = {
	suggestions: string[];
	loading: boolean;
	raw: string;
};

let state: SuggestionState = {
	suggestions: [],
	loading: false,
	raw: ""
};

const listeners = new Set<() => void>();

function emit(): void {
	for (const listener of listeners) {
		listener();
	}
}

export const suggestionStore = {
	setLoading(loading: boolean): void {
		if (state.loading === loading) {
			return;
		}
		state = {
			...state,
			loading
		};
		emit();
	},

	setSuggestions(items: string[], raw = ""): void {
		state = {
			...state,
			suggestions: [...items],
			raw,
			loading: false
		};
		emit();
	},

	clearSuggestions(): void {
		state = {
			...state,
			suggestions: [],
			raw: "",
			loading: false
		};
		emit();
	},

	getSnapshot(): SuggestionState {
		return state;
	},

	subscribe(listener: () => void): () => void {
		listeners.add(listener);
		return () => listeners.delete(listener);
	}
};

export function useSuggestionStore(): SuggestionState {
	return useSyncExternalStore(suggestionStore.subscribe, suggestionStore.getSnapshot, suggestionStore.getSnapshot);
}
