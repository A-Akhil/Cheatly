import { useSyncExternalStore } from "react";
import { apiClient } from "./api_client";
import { WebsocketClient } from "./websocket_client";

type ConnectionState = {
	websocketConnected: boolean;
	apiReachable: boolean;
};

let state: ConnectionState = {
	websocketConnected: false,
	apiReachable: false
};

const listeners = new Set<() => void>();
let wsClient: WebsocketClient | null = null;

function emit(): void {
	for (const listener of listeners) {
		listener();
	}
}

export const connectionManager = {
	async start(): Promise<void> {
		if (wsClient) {
			return;
		}

		try {
			await apiClient.health();
			state = {
				...state,
				apiReachable: true
			};
		} catch {
			state = {
				...state,
				apiReachable: false
			};
		}
		emit();

		wsClient = new WebsocketClient(apiClient.baseUrl, (connected) => {
			state = {
				...state,
				websocketConnected: connected
			};
			emit();
		});
		wsClient.connect();
	},

	stop(): void {
		wsClient?.disconnect();
		wsClient = null;
		state = {
			...state,
			websocketConnected: false
		};
		emit();
	},

	getSnapshot(): ConnectionState {
		return state;
	},

	subscribe(listener: () => void): () => void {
		listeners.add(listener);
		return () => listeners.delete(listener);
	}
};

export function useConnectionState(): ConnectionState {
	return useSyncExternalStore(connectionManager.subscribe, connectionManager.getSnapshot, connectionManager.getSnapshot);
}
