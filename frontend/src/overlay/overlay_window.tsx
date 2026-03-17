import React, { useEffect, useRef } from "react";
import { apiClient } from "../services/api_client";
import { connectionManager, useConnectionState } from "../services/connection_manager";
import { settingsStore } from "../state/settings_store";
import { dragManager } from "./drag_manager";
import { opacityController } from "./opacity_controller";
import { OverlayContainer } from "./overlay_container";

export function OverlayWindow(): JSX.Element {
	const { apiReachable, websocketConnected } = useConnectionState();
	const rootRef = useRef<HTMLDivElement | null>(null);

	useEffect(() => {
		void connectionManager.start();
		return () => connectionManager.stop();
	}, []);

	useEffect(() => {
		const hydrate = async (): Promise<void> => {
			try {
				const config = await apiClient.getSettings();
				settingsStore.setFromBackend(config as Record<string, unknown>);
			} catch {
				// Keep defaults if backend settings are unavailable.
			}
		};
		void hydrate();
	}, []);

	useEffect(() => {
		const root = rootRef.current;
		if (!root) {
			return;
		}

		const handle = root.querySelector("#overlay-drag-handle");
		if (!(handle instanceof HTMLElement)) {
			return;
		}

		const detach = dragManager.attach(handle, root);
		return detach;
	}, [rootRef.current]);

	useEffect(() => {
		const snapshot = settingsStore.getSnapshot();
		opacityController.setOpacity(snapshot.opacity);
	}, []);

	const connectionLabel = !apiReachable
		? "API disconnected"
		: websocketConnected
			? "Connected"
			: "WebSocket reconnecting";

	const connectionColor = !apiReachable ? "#ff8a8a" : websocketConnected ? "#8dff8d" : "#ffd18d";

	return (
		<div
			id="cheatly-overlay-root"
			ref={rootRef}
			style={{
				position: "fixed",
				left: 24,
				top: 24,
				zIndex: 999999,
				opacity: 0.95
			}}
		>
			<div style={{ marginBottom: 6, fontSize: 11, color: connectionColor }}>{connectionLabel}</div>
			<OverlayContainer />
		</div>
	);
}
