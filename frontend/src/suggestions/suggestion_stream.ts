import { suggestionStore } from "../state/suggestion_store";

type SuggestionsPayload = {
	suggestions?: string[];
	raw?: string;
};

export const suggestionStream = {
	applyPayload(payload: SuggestionsPayload): void {
		suggestionStore.setSuggestions(payload.suggestions ?? [], payload.raw ?? "");
	},

	clear(): void {
		suggestionStore.clearSuggestions();
	}
};
