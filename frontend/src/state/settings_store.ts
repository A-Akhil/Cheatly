import { useSyncExternalStore } from "react";

export type SettingsState = {
	loaded: boolean;
	provider: string;
	googleModel: string;
	ollamaModel: string;
	opacity: number;
	ragTopK: number;
};

let state: SettingsState = {
	loaded: false,
	provider: "mock",
	googleModel: "gemma-3-1b-it",
	ollamaModel: "llama3",
	opacity: 0.95,
	ragTopK: 5
};

const listeners = new Set<() => void>();

function emit(): void {
	for (const listener of listeners) {
		listener();
	}
}

export const settingsStore = {
	setFromBackend(config: Record<string, any>): void {
		const mp = config.model_provider ?? {};
		const rag = config.rag ?? {};
		state = {
			...state,
			provider: String(mp.provider ?? state.provider),
			googleModel: String(mp.google_model ?? state.googleModel),
			ollamaModel: String(mp.ollama_model ?? state.ollamaModel),
			ragTopK: Number(rag.top_k ?? state.ragTopK),
			loaded: true
		};
		emit();
	},

	patch(next: Partial<SettingsState>): void {
		state = {
			...state,
			...next
		};
		emit();
	},

	getSnapshot(): SettingsState {
		return state;
	},

	subscribe(listener: () => void): () => void {
		listeners.add(listener);
		return () => listeners.delete(listener);
	}
};

export function useSettingsStore(): SettingsState {
	return useSyncExternalStore(settingsStore.subscribe, settingsStore.getSnapshot, settingsStore.getSnapshot);
}
