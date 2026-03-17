from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml


class ConfigLoader:
	def __init__(self, base_dir: str | Path) -> None:
		self.base_dir = Path(base_dir)
		self.default_path = self.base_dir / "default_config.yaml"
		self.user_path = self.base_dir / "user_config.yaml"
		self._config: dict[str, Any] = {}
		self.reload()

	def reload(self) -> dict[str, Any]:
		default_cfg = self._read_yaml(self.default_path)
		user_cfg = self._read_yaml(self.user_path)

		merged = self._deep_merge(default_cfg, user_cfg)
		self._apply_env_overrides(merged)
		self._config = merged
		return copy.deepcopy(self._config)

	def get_all(self) -> dict[str, Any]:
		return copy.deepcopy(self._config)

	def get(self, key_path: str, default: Any = None) -> Any:
		current: Any = self._config
		for part in key_path.split("."):
			if not isinstance(current, dict) or part not in current:
				return default
			current = current[part]
		return current

	def save_user_overrides(self, updates: dict[str, Any]) -> dict[str, Any]:
		current_user = self._read_yaml(self.user_path)
		merged_user = self._deep_merge(current_user, updates)
		self.user_path.parent.mkdir(parents=True, exist_ok=True)
		with self.user_path.open("w", encoding="utf-8") as fp:
			yaml.safe_dump(merged_user, fp, sort_keys=False)
		return self.reload()

	@staticmethod
	def _read_yaml(path: Path) -> dict[str, Any]:
		if not path.exists():
			return {}
		with path.open("r", encoding="utf-8") as fp:
			loaded = yaml.safe_load(fp) or {}
		if not isinstance(loaded, dict):
			raise ValueError(f"Invalid config format in {path}")
		return loaded

	@staticmethod
	def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
		result = copy.deepcopy(base)
		for key, value in override.items():
			if isinstance(value, dict) and isinstance(result.get(key), dict):
				result[key] = ConfigLoader._deep_merge(result[key], value)
			else:
				result[key] = value
		return result

	@staticmethod
	def _apply_env_overrides(config: dict[str, Any]) -> None:
		gemini_key = os.getenv("GEMINI_API_KEY")
		model_override = os.getenv("CHEATLY_MODEL")
		provider_override = os.getenv("CHEATLY_PROVIDER")

		if provider_override:
			config.setdefault("model_provider", {})["provider"] = provider_override.strip().lower()

		if model_override:
			config.setdefault("model_provider", {})["google_model"] = model_override.strip()

		if gemini_key:
			config.setdefault("model_provider", {})["_gemini_key_present"] = True
