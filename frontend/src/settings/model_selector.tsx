import React from "react";

type Props = {
	provider: string;
	googleModel: string;
	ollamaModel: string;
	onChange: (next: { provider?: string; googleModel?: string; ollamaModel?: string }) => void;
};

export function ModelSelector({ provider, googleModel, ollamaModel, onChange }: Props): JSX.Element {
	return (
		<div style={{ marginBottom: 10 }}>
			<h4 style={{ margin: "0 0 6px 0", fontSize: 13 }}>Model Provider</h4>
			<div style={{ display: "grid", gap: 6 }}>
				<select value={provider} onChange={(event) => onChange({ provider: event.target.value })}>
					<option value="mock">mock</option>
					<option value="google">google</option>
					<option value="ollama">ollama</option>
				</select>

				<input
					value={googleModel}
					onChange={(event) => onChange({ googleModel: event.target.value })}
					placeholder="Google model"
				/>

				<input
					value={ollamaModel}
					onChange={(event) => onChange({ ollamaModel: event.target.value })}
					placeholder="Ollama model"
				/>
			</div>
		</div>
	);
}
