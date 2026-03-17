#[derive(serde::Serialize)]
pub struct PermissionStatus {
	pub microphone_granted: bool,
	pub notes: String,
}

pub fn check_permissions() -> PermissionStatus {
	PermissionStatus {
		microphone_granted: true,
		notes: "Runtime permission probe is a placeholder; real platform checks should be added per OS.".into(),
	}
}
