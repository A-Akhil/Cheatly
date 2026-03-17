import React from "react";

type Props = {
	sampleRate: number;
	channels: number;
};

export function AudioSettings({ sampleRate, channels }: Props): JSX.Element {
	return (
		<div style={{ marginBottom: 10 }}>
			<h4 style={{ margin: "0 0 6px 0", fontSize: 13 }}>Audio</h4>
			<div style={{ fontSize: 12, opacity: 0.9 }}>
				<div>Sample rate: {sampleRate}</div>
				<div>Channels: {channels}</div>
			</div>
		</div>
	);
}
