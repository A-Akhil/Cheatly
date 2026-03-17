mod backend_launcher;
mod permissions;
mod window_manager;

use std::path::PathBuf;

use backend_launcher::{start_backend, stop_backend, BackendProcessHandle};

fn main() {
	let backend_handle = BackendProcessHandle::new();
	let backend_handle_for_setup = backend_handle.clone();
	let backend_handle_for_exit = backend_handle.clone();

	tauri::Builder::default()
		.setup(move |app| {
			let app_dir: PathBuf = std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
			let _permission_status = permissions::check_permissions();
			let _ = start_backend(&backend_handle_for_setup, &app_dir);
			window_manager::configure_main_window(app.handle());
			Ok(())
		})
		.invoke_handler(tauri::generate_handler![
			window_manager::set_overlay_position,
			window_manager::set_overlay_opacity
		])
		.on_window_event(move |event| {
			if let tauri::WindowEvent::Destroyed = event.event() {
				stop_backend(&backend_handle_for_exit);
			}
		})
		.run(tauri::generate_context!())
		.expect("error while running Cheatly Tauri app");
}
