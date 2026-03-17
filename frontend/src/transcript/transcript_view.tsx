import React, { useState } from "react";
import { apiClient } from "../services/api_client";
import { connectionManager } from "../services/connection_manager";
import { suggestionStore } from "../state/suggestion_store";
import { transcriptStore, useTranscriptStore } from "../state/transcript_store";

export function TranscriptView(): JSX.Element {
	const { segments } = useTranscriptStore();
	const [draft, setDraft] = useState("");
	const [error, setError] = useState("");

	const submit = async (): Promise<void> => {
		const text = draft.trim();
		if (!text) {
			return;
		}
		setError("");
		suggestionStore.setLoading(true);
		setDraft("");

		try {
			const response = await apiClient.ingestTranscript(text);
			if (!connectionManager.getSnapshot().websocketConnected) {
				transcriptStore.appendSegment(response.result.transcript);
			}
			suggestionStore.setSuggestions(response.result.suggestions, response.result.raw);
		} catch (err) {
			suggestionStore.setLoading(false);
			setError(err instanceof Error ? err.message : "Failed to ingest transcript");
		}
	};

	return (
		<section style={{ marginBottom: 12 }}>
			<h3 style={{ margin: "0 0 8px 0", fontSize: 14 }}>Transcript</h3>
			<div style={{ marginBottom: 6, fontSize: 11, opacity: 0.75 }}>
				Manual test input. Meeting audio capture is not wired here yet.
			</div>
			<div
				style={{
					maxHeight: 120,
					overflowY: "auto",
					background: "rgba(255,255,255,0.08)",
					padding: 8,
					borderRadius: 8,
					marginBottom: 8,
					fontSize: 13
				}}
			>
				{segments.length === 0 ? "No transcript yet." : segments.map((item, idx) => <div key={`${idx}-${item}`}>{item}</div>)}
			</div>

			<textarea
				value={draft}
				onChange={(event) => setDraft(event.target.value)}
				placeholder="Manual transcript test input (not Google Meet capture)"
				rows={3}
				style={{ width: "100%", resize: "vertical", borderRadius: 8, border: "1px solid #666", padding: 8 }}
			/>

			<div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
				<button onClick={submit}>Send transcript</button>
				{error ? <span style={{ color: "#ff8a8a", fontSize: 12 }}>{error}</span> : null}
			</div>
		</section>
	);
}
