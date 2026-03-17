const BASE_URL = (import.meta as ImportMeta & { env?: Record<string, string> }).env?.VITE_BACKEND_URL ?? "http://127.0.0.1:8765";

export type AppSettings = Record<string, unknown>;

export type IngestResult = {
	transcript: string;
	suggestions: string[];
	retrieved: Array<{ document_id: string; source_name: string; score: number }>;
	raw: string;
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
	const response = await fetch(`${BASE_URL}${path}`, {
		headers: {
			"Content-Type": "application/json",
			...(options?.headers ?? {})
		},
		...options
	});

	if (!response.ok) {
		const detail = await response.text();
		throw new Error(`HTTP ${response.status}: ${detail}`);
	}

	return response.json() as Promise<T>;
}

export const apiClient = {
	baseUrl: BASE_URL,

	health: () => request<{ status: string; provider: string }>("/health"),

	getModels: () =>
		request<{
			provider: string;
			google_model: string;
			google_fallback_model: string;
			ollama_model: string;
		}>("/models"),

	getSettings: () => request<AppSettings>("/settings"),

	updateSettings: (payload: Record<string, unknown>) =>
		request<{ ok: boolean; config: AppSettings }>("/settings", {
			method: "POST",
			body: JSON.stringify(payload)
		}),

	resetSession: () => request<{ ok: boolean; session_id: string }>("/session/reset", { method: "POST" }),

	ingestTranscript: (text: string) =>
		request<{ ok: boolean; result: IngestResult }>("/transcript/ingest", {
			method: "POST",
			body: JSON.stringify({ text })
		}),

	listRagDocuments: () =>
		request<{ documents: Array<{ id: string; source_name: string; created_at: string }> }>("/rag/documents"),

	ingestRagText: (source_name: string, text: string) =>
		request<{ ok: boolean; document_id: string }>("/rag/documents/text", {
			method: "POST",
			body: JSON.stringify({ source_name, text })
		}),

	ingestRagFile: async (file: File) => {
		const form = new FormData();
		form.append("file", file);

		const response = await fetch(`${BASE_URL}/rag/documents/file`, {
			method: "POST",
			body: form
		});

		if (!response.ok) {
			const detail = await response.text();
			throw new Error(`HTTP ${response.status}: ${detail}`);
		}

		return response.json() as Promise<{ ok: boolean; document_id: string }>;
	},

	deleteRagDocument: (id: string) => request<{ ok: boolean }>(`/rag/documents/${id}`, { method: "DELETE" })
};
