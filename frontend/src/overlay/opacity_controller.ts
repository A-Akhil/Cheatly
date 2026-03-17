import { settingsStore } from "../state/settings_store";
import { invokeTauri, isTauriRuntime } from "../services/tauri_bridge";

export const opacityController = {
	setOpacity(value: number): void {
		const clamped = Math.min(1, Math.max(0.4, value));
		const root = document.getElementById("cheatly-overlay-root");
		if (root) {
			root.style.opacity = String(clamped);
		}
		if (isTauriRuntime()) {
			void invokeTauri("set_overlay_opacity", { opacity: clamped });
		}
		settingsStore.patch({ opacity: clamped });
	}
};
