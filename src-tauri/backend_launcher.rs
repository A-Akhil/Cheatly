use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};

#[derive(Clone)]
pub struct BackendProcessHandle {
	pub child: Arc<Mutex<Option<Child>>>,
}

impl BackendProcessHandle {
	pub fn new() -> Self {
		Self {
			child: Arc::new(Mutex::new(None)),
		}
	}
}

pub fn start_backend(handle: &BackendProcessHandle, app_dir: &PathBuf) -> Result<(), String> {
	let backend_main = app_dir.join("backend").join("main.py");

	let mut command = if cfg!(target_os = "windows") {
		let mut c = Command::new("python");
		c.arg("-m").arg("uvicorn").arg("backend.main:app").arg("--host").arg("127.0.0.1").arg("--port").arg("8765");
		c
	} else {
		let mut c = Command::new("python");
		c.arg("-m").arg("uvicorn").arg("backend.main:app").arg("--host").arg("127.0.0.1").arg("--port").arg("8765");
		c
	};

	let child = command
		.current_dir(app_dir)
		.env("PYTHONUNBUFFERED", "1")
		.stdin(Stdio::null())
		.stdout(Stdio::null())
		.stderr(Stdio::null())
		.spawn()
		.map_err(|e| format!("Failed to launch backend at {:?}: {}", backend_main, e))?;

	if let Ok(mut lock) = handle.child.lock() {
		*lock = Some(child);
	}

	Ok(())
}

pub fn stop_backend(handle: &BackendProcessHandle) {
	if let Ok(mut lock) = handle.child.lock() {
		if let Some(child) = lock.as_mut() {
			let _ = child.kill();
			let _ = child.wait();
		}
		*lock = None;
	}
}
