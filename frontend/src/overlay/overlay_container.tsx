import React, { useState } from "react";
import { SettingsPanel } from "../settings/settings_panel";
import { SuggestionPanel } from "../suggestions/suggestion_panel";
import { TranscriptView } from "../transcript/transcript_view";

export function OverlayContainer(): JSX.Element {
	const [settingsOpen, setSettingsOpen] = useState(false);

	return (
		<div
			style={{
				position: "relative",
				width: 460,
				background: "rgba(22,22,22,0.92)",
				color: "#f2f2f2",
				border: "1px solid rgba(255,255,255,0.15)",
				borderRadius: 12,
				padding: 12,
				boxShadow: "0 8px 24px rgba(0,0,0,0.35)"
			}}
		>
			<div id="overlay-drag-handle" style={{ cursor: "move", marginBottom: 8, fontSize: 12, opacity: 0.8 }}>
				Cheatly Overlay (drag here)
			</div>

			<div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
				<strong style={{ fontSize: 14 }}>Live Assistant</strong>
				<button onClick={() => setSettingsOpen((v) => !v)}>{settingsOpen ? "Close settings" : "Open settings"}</button>
			</div>

			<TranscriptView />
			<SuggestionPanel />

			{settingsOpen ? <SettingsPanel onClose={() => setSettingsOpen(false)} /> : null}
		</div>
	);
}
