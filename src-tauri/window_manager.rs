use tauri::{Manager, Runtime, Window};

#[tauri::command]
pub fn set_overlay_position<R: Runtime>(window: Window<R>, x: f64, y: f64) -> Result<(), String> {
	window
		.set_position(tauri::Position::Physical(tauri::PhysicalPosition { x: x as i32, y: y as i32 }))
		.map_err(|e| e.to_string())
}

#[tauri::command]
pub fn set_overlay_opacity<R: Runtime>(window: Window<R>, opacity: f64) -> Result<(), String> {
	let clamped = opacity.clamp(0.4, 1.0);
	window.set_opacity(clamped).map_err(|e| e.to_string())
}

pub fn configure_main_window<R: Runtime>(app: &tauri::AppHandle<R>) {
	if let Some(window) = app.get_webview_window("main") {
		let _ = window.set_always_on_top(true);
		let _ = window.set_decorations(false);
		let _ = window.set_shadow(false);
		let _ = window.set_skip_taskbar(true);

		#[cfg(target_os = "windows")]
		{
			apply_windows_capture_exclusion(&window);
		}
	}
}

#[cfg(target_os = "windows")]
fn apply_windows_capture_exclusion<R: Runtime>(window: &Window<R>) {
	use windows::Win32::Foundation::HWND;
	use windows::Win32::UI::WindowsAndMessaging::{SetWindowDisplayAffinity, WDA_EXCLUDEFROMCAPTURE};

	if let Ok(hwnd) = window.hwnd() {
		unsafe {
			let _ = SetWindowDisplayAffinity(HWND(hwnd.0), WDA_EXCLUDEFROMCAPTURE);
		}
	}
}
