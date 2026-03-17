import { suggestionStream } from "../suggestions/suggestion_stream";
import { transcriptBuffer } from "../transcript/transcript_buffer";

type ConnectionCallback = (connected: boolean) => void;

export class WebsocketClient {
	private socket: WebSocket | null = null;
	private reconnectTimer: number | null = null;
	private retries = 0;
	private intentionallyClosed = false;
	private readonly url: string;
	private readonly onConnection: ConnectionCallback;

	constructor(baseHttpUrl: string, onConnection: ConnectionCallback) {
		const wsBase = baseHttpUrl.replace(/^http/, "ws");
		this.url = `${wsBase}/ws`;
		this.onConnection = onConnection;
	}

	connect(): void {
		if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
			return;
		}

		this.intentionallyClosed = false;

		this.socket = new WebSocket(this.url);
		this.socket.onopen = () => {
			this.retries = 0;
			this.onConnection(true);
			this.socket?.send("ping");
		};

		this.socket.onmessage = (event) => {
			try {
				const message = JSON.parse(event.data as string) as {
					type?: string;
					payload?: Record<string, unknown>;
				};

				if (message.type === "suggestions" && message.payload) {
					suggestionStream.applyPayload({
						suggestions: (message.payload.suggestions as string[]) ?? [],
						raw: (message.payload.raw as string) ?? ""
					});
					if (typeof message.payload.transcript === "string") {
						transcriptBuffer.push(message.payload.transcript);
					}
				}

				if (message.type === "session_reset") {
					transcriptBuffer.clear();
					suggestionStream.clear();
				}
			} catch {
				// Ignore malformed frames.
			}
		};

		this.socket.onclose = () => {
			this.onConnection(false);
			if (!this.intentionallyClosed) {
				this.scheduleReconnect();
			}
		};

		this.socket.onerror = () => {
			this.onConnection(false);
			if (!this.intentionallyClosed) {
				this.socket?.close();
			}
		};
	}

	disconnect(): void {
		this.intentionallyClosed = true;
		if (this.reconnectTimer) {
			window.clearTimeout(this.reconnectTimer);
			this.reconnectTimer = null;
		}
		this.socket?.close();
		this.socket = null;
	}

	private scheduleReconnect(): void {
		if (this.reconnectTimer !== null) {
			return;
		}
		const waitMs = Math.min(5000, 500 * 2 ** this.retries);
		this.retries += 1;
		this.reconnectTimer = window.setTimeout(() => {
			this.reconnectTimer = null;
			this.connect();
		}, waitMs);
	}
}
