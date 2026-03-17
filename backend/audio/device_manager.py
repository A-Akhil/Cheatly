from __future__ import annotations


class DeviceManager:
	def list_input_devices(self) -> list[dict]:
		return [{"id": 0, "name": "default", "sample_rate": 16000, "channels": 1}]
