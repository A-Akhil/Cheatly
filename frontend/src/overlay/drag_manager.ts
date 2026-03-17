type Cleanup = () => void;

import { invokeTauri, isTauriRuntime } from "../services/tauri_bridge";

export const dragManager = {
	attach(handle: HTMLElement, target: HTMLElement): Cleanup {
		let dragging = false;
		let offsetX = 0;
		let offsetY = 0;

		const onMouseDown = (event: MouseEvent): void => {
			dragging = true;
			const rect = target.getBoundingClientRect();
			offsetX = event.clientX - rect.left;
			offsetY = event.clientY - rect.top;
			target.style.position = "fixed";
			document.body.style.userSelect = "none";
		};

		const onMouseMove = (event: MouseEvent): void => {
			if (!dragging) {
				return;
			}
			target.style.left = `${Math.max(8, event.clientX - offsetX)}px`;
			target.style.top = `${Math.max(8, event.clientY - offsetY)}px`;
		};

		const onMouseUp = (): void => {
			dragging = false;
			document.body.style.userSelect = "";
			if (isTauriRuntime()) {
				const x = Number.parseFloat(target.style.left || "0") || 0;
				const y = Number.parseFloat(target.style.top || "0") || 0;
				void invokeTauri("set_overlay_position", { x, y });
			}
		};

		handle.addEventListener("mousedown", onMouseDown);
		window.addEventListener("mousemove", onMouseMove);
		window.addEventListener("mouseup", onMouseUp);

		return () => {
			handle.removeEventListener("mousedown", onMouseDown);
			window.removeEventListener("mousemove", onMouseMove);
			window.removeEventListener("mouseup", onMouseUp);
		};
	}
};
