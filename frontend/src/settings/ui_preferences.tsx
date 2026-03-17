import React from "react";
import { opacityController } from "../overlay/opacity_controller";

type Props = {
	opacity: number;
	ragTopK: number;
	onChange: (next: { opacity?: number; ragTopK?: number }) => void;
};

export function UiPreferences({ opacity, ragTopK, onChange }: Props): JSX.Element {
	return (
		<div style={{ marginBottom: 10 }}>
			<h4 style={{ margin: "0 0 6px 0", fontSize: 13 }}>UI + RAG</h4>
			<label style={{ display: "block", marginBottom: 6, fontSize: 12 }}>
				Opacity: {opacity.toFixed(2)}
			</label>
			<input
				type="range"
				min={0.4}
				max={1}
				step={0.01}
				value={opacity}
				onChange={(event) => {
					const value = Number(event.target.value);
					onChange({ opacity: value });
					opacityController.setOpacity(value);
				}}
			/>

			<label style={{ display: "block", margin: "8px 0 6px", fontSize: 12 }}>RAG top_k</label>
			<input
				type="number"
				min={1}
				max={20}
				value={ragTopK}
				onChange={(event) => onChange({ ragTopK: Number(event.target.value) || 1 })}
			/>
		</div>
	);
}
