import React, { useEffect, useState } from "react";
import { apiClient } from "../services/api_client";
import { settingsStore, useSettingsStore } from "../state/settings_store";
import { AudioSettings } from "./audio_settings";
import { ModelSelector } from "./model_selector";
import { UiPreferences } from "./ui_preferences";

type Props = {
	onClose: () => void;
};

export function SettingsPanel({ onClose }: Props): JSX.Element {
	const current = useSettingsStore();
	const [provider, setProvider] = useState(current.provider);
	const [googleModel, setGoogleModel] = useState(current.googleModel);
	const [ollamaModel, setOllamaModel] = useState(current.ollamaModel);
	const [opacity, setOpacity] = useState(current.opacity);
	const [ragTopK, setRagTopK] = useState(current.ragTopK);
	const [ragSourceName, setRagSourceName] = useState("manual-note");
	const [ragText, setRagText] = useState("");
	const [ragDocs, setRagDocs] = useState<Array<{ id: string; source_name: string; created_at: string }>>([]);
	const [status, setStatus] = useState("");

	const refreshRagDocs = async (): Promise<void> => {
		const res = await apiClient.listRagDocuments();
		setRagDocs(res.documents);
	};

	useEffect(() => {
		void refreshRagDocs();
	}, []);

	const saveSettings = async (): Promise<void> => {
		setStatus("Saving settings...");
		try {
			const payload = {
				model_provider: {
					provider,
					google_model: googleModel,
					ollama_model: ollamaModel
				},
				rag: {
					top_k: ragTopK
				}
			};
			const updated = await apiClient.updateSettings(payload);
			settingsStore.setFromBackend(updated.config as Record<string, unknown>);
			settingsStore.patch({ opacity });
			setStatus("Settings saved");
		} catch (error) {
			setStatus(error instanceof Error ? error.message : "Failed to save settings");
		}
	};

	const ingestText = async (): Promise<void> => {
		if (!ragText.trim()) {
			return;
		}
		setStatus("Ingesting text...");
		await apiClient.ingestRagText(ragSourceName, ragText);
		setRagText("");
		await refreshRagDocs();
		setStatus("RAG text ingested");
	};

	const ingestFile = async (event: React.ChangeEvent<HTMLInputElement>): Promise<void> => {
		const file = event.target.files?.[0];
		if (!file) {
			return;
		}
		setStatus(`Uploading ${file.name}...`);
		await apiClient.ingestRagFile(file);
		await refreshRagDocs();
		setStatus("RAG file ingested");
		event.target.value = "";
	};

	const deleteDoc = async (id: string): Promise<void> => {
		await apiClient.deleteRagDocument(id);
		await refreshRagDocs();
	};

	return (
		<div
			style={{
				position: "absolute",
				inset: 0,
				background: "rgba(12,12,12,0.96)",
				padding: 12,
				overflowY: "auto",
				borderRadius: 12
			}}
		>
			<div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
				<strong>Settings + RAG</strong>
				<button onClick={onClose}>Close</button>
			</div>

			<ModelSelector
				provider={provider}
				googleModel={googleModel}
				ollamaModel={ollamaModel}
				onChange={(next) => {
					if (next.provider !== undefined) {
						setProvider(next.provider);
					}
					if (next.googleModel !== undefined) {
						setGoogleModel(next.googleModel);
					}
					if (next.ollamaModel !== undefined) {
						setOllamaModel(next.ollamaModel);
					}
				}}
			/>

			<AudioSettings sampleRate={16000} channels={1} />

			<UiPreferences
				opacity={opacity}
				ragTopK={ragTopK}
				onChange={(next) => {
					if (next.opacity !== undefined) {
						setOpacity(next.opacity);
					}
					if (next.ragTopK !== undefined) {
						setRagTopK(next.ragTopK);
					}
				}}
			/>

			<div style={{ marginBottom: 10 }}>
				<h4 style={{ margin: "0 0 6px 0", fontSize: 13 }}>RAG Text Ingestion</h4>
				<input
					value={ragSourceName}
					onChange={(event) => setRagSourceName(event.target.value)}
					placeholder="Source name"
					style={{ width: "100%", marginBottom: 6 }}
				/>
				<textarea
					value={ragText}
					onChange={(event) => setRagText(event.target.value)}
					rows={4}
					placeholder="Paste reference text"
					style={{ width: "100%", marginBottom: 6 }}
				/>
				<div style={{ display: "flex", gap: 8 }}>
					<button onClick={() => void ingestText()}>Ingest text</button>
					<label style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
						<span>Upload file</span>
						<input type="file" onChange={(event) => void ingestFile(event)} />
					</label>
				</div>
			</div>

			<div style={{ marginBottom: 10 }}>
				<h4 style={{ margin: "0 0 6px 0", fontSize: 13 }}>RAG Documents</h4>
				{ragDocs.length === 0 ? <div style={{ fontSize: 12 }}>No documents ingested.</div> : null}
				{ragDocs.map((doc) => (
					<div key={doc.id} style={{ display: "flex", justifyContent: "space-between", gap: 8, marginBottom: 4 }}>
						<span style={{ fontSize: 12 }}>
							{doc.source_name} ({doc.id.slice(0, 8)}...)
						</span>
						<button onClick={() => void deleteDoc(doc.id)}>Delete</button>
					</div>
				))}
			</div>

			<div style={{ display: "flex", gap: 8 }}>
				<button onClick={() => void saveSettings()}>Save settings</button>
				<button
					onClick={() => {
						void apiClient.resetSession();
						setStatus("Session reset");
					}}
				>
					Reset session
				</button>
			</div>

			{status ? <div style={{ marginTop: 8, fontSize: 12 }}>{status}</div> : null}
		</div>
	);
}
