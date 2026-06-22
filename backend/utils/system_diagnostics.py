from __future__ import annotations

import json
import logging
import multiprocessing as mp
import os
import platform
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


def _package_version(name: str) -> str:
    try:
        return metadata.version(name)
    except Exception:
        return "unavailable"


def collect_system_diagnostics(config: dict[str, Any]) -> dict[str, Any]:
    stt_cfg = config.get("speech_recognition", {})

    diagnostics: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": {
            "version": sys.version,
            "executable": sys.executable,
            "implementation": platform.python_implementation(),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "process": {
            "pid": os.getpid(),
            "cwd": os.getcwd(),
            "mp_start_method": mp.get_start_method(allow_none=True),
        },
        "packages": {
            "faster-whisper": _package_version("faster-whisper"),
            "ctranslate2": _package_version("ctranslate2"),
            "numpy": _package_version("numpy"),
            "huggingface-hub": _package_version("huggingface-hub"),
            "litellm": _package_version("litellm"),
            "sounddevice": _package_version("sounddevice"),
            "pyaudiowpatch": _package_version("pyaudiowpatch"),
        },
        "stt_config": {
            "enabled": bool(stt_cfg.get("enabled", False)),
            "preload_on_startup": bool(stt_cfg.get("preload_on_startup", False)),
            "require_preload_success": bool(stt_cfg.get("require_preload_success", False)),
            "model_size": stt_cfg.get("model_size"),
            "device": stt_cfg.get("device"),
            "compute_type": stt_cfg.get("compute_type"),
            "cpu_threads": stt_cfg.get("cpu_threads"),
            "num_workers": stt_cfg.get("num_workers"),
            "use_mkl": stt_cfg.get("use_mkl"),
            "isolate_process": stt_cfg.get("isolate_process"),
            "model_cache_dir": stt_cfg.get("model_cache_dir"),
        },
        "environment": {
            "OMP_NUM_THREADS": os.getenv("OMP_NUM_THREADS"),
            "CT2_USE_MKL": os.getenv("CT2_USE_MKL"),
            "HF_HOME": os.getenv("HF_HOME"),
            "HF_HUB_DISABLE_SYMLINKS_WARNING": os.getenv("HF_HUB_DISABLE_SYMLINKS_WARNING"),
            "PATH_head": os.getenv("PATH", "").split(os.pathsep)[:8],
            "PROCESSOR_IDENTIFIER": os.getenv("PROCESSOR_IDENTIFIER"),
            "NUMBER_OF_PROCESSORS": os.getenv("NUMBER_OF_PROCESSORS"),
        },
    }

    return diagnostics


def write_system_diagnostics(config: dict[str, Any]) -> str:
    diagnostics = collect_system_diagnostics(config)
    logging_cfg = config.get("logging", {})
    path = Path(str(logging_cfg.get("system_diag_file_path", "./backend/logging/system_diagnostics.log")))
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(diagnostics, ensure_ascii=False) + "\n")

    logger.info(f"[diag] system diagnostics written to {path}")
    return str(path)
