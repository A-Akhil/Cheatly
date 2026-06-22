from __future__ import annotations

from multiprocessing import Queue
from typing import Any
from pathlib import Path
import faulthandler
import time
import traceback
import platform
import sys
import os
import ctypes
from importlib import metadata


def _write_worker_trace(log_file: Path, message: str) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8", errors="ignore") as fp:
        fp.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")


def _resolve_local_whisper_snapshot(cache_root: Path, model_size: str) -> str | None:
    repo_dir = cache_root / f"models--Systran--faster-whisper-{model_size}"
    refs_main = repo_dir / "refs" / "main"
    if not refs_main.exists():
        return None

    try:
        revision = refs_main.read_text(encoding="utf-8", errors="ignore").strip()
    except Exception:
        return None

    if not revision:
        return None

    snap_dir = repo_dir / "snapshots" / revision
    required = ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]
    if snap_dir.is_dir() and all((snap_dir / f).exists() for f in required):
        return str(snap_dir)
    return None


def _log_windows_loaded_modules(log_file: Path, max_items: int = 120) -> None:
    if platform.system().lower() != "windows":
        _write_worker_trace(log_file, "dll trace skipped: non-windows platform")
        return

    try:
        psapi = ctypes.WinDLL("Psapi.dll")
        kernel32 = ctypes.WinDLL("Kernel32.dll")

        LIST_MODULES_ALL = 0x03
        process = kernel32.GetCurrentProcess()

        arr_size = 2048
        HMODULE = ctypes.c_void_p
        modules = (HMODULE * arr_size)()
        needed = ctypes.c_ulong()

        ok = psapi.EnumProcessModulesEx(
            process,
            ctypes.byref(modules),
            ctypes.sizeof(modules),
            ctypes.byref(needed),
            LIST_MODULES_ALL,
        )
        if not ok:
            _write_worker_trace(log_file, "dll trace failed: EnumProcessModulesEx returned false")
            return

        count = int(needed.value // ctypes.sizeof(HMODULE))
        _write_worker_trace(log_file, f"dll trace module_count={count}")

        buf = ctypes.create_unicode_buffer(32768)
        for idx in range(min(count, max_items)):
            module = modules[idx]
            copied = psapi.GetModuleFileNameExW(process, module, buf, len(buf))
            path = buf.value if copied else "<unresolved>"
            _write_worker_trace(log_file, f"dll[{idx}]={path}")
    except Exception as exc:
        _write_worker_trace(log_file, f"dll trace exception: {exc}")


def _log_ctranslate2_runtime(log_file: Path) -> None:
    try:
        import ctranslate2  # type: ignore

        version = getattr(ctranslate2, "__version__", "unknown")
        _write_worker_trace(log_file, f"ctranslate2.runtime.version={version}")

        try:
            cpu_types = ctranslate2.get_supported_compute_types("cpu")
            _write_worker_trace(log_file, f"ctranslate2.runtime.cpu_compute_types={sorted(list(cpu_types))}")
        except Exception as exc:
            _write_worker_trace(log_file, f"ctranslate2.runtime.cpu_compute_types.error={exc}")

        try:
            cuda_types = ctranslate2.get_supported_compute_types("cuda")
            _write_worker_trace(log_file, f"ctranslate2.runtime.cuda_compute_types={sorted(list(cuda_types))}")
        except Exception as exc:
            _write_worker_trace(log_file, f"ctranslate2.runtime.cuda_compute_types.error={exc}")

    except Exception as exc:
        _write_worker_trace(log_file, f"ctranslate2.runtime.import.error={exc}")


def run_whisper_worker(task_queue: Queue, result_queue: Queue, config: dict[str, Any]) -> None:
    model_size = str(config.get("model_size", "base"))
    device = str(config.get("device", "cpu"))
    compute_type = str(config.get("compute_type", "float32"))
    language = str(config.get("language", "en"))
    model_cache_dir = str(config.get("model_cache_dir", "./models/whisper"))
    cpu_threads = int(config.get("cpu_threads", 1))
    num_workers = int(config.get("num_workers", 1))
    use_mkl = bool(config.get("use_mkl", False))
    worker_fault_file = Path(str(config.get("worker_fault_file", "./backend/logging/whisper_worker_fault.log")))

    os.environ.setdefault("OMP_NUM_THREADS", str(max(1, cpu_threads)))
    os.environ.setdefault("CT2_USE_MKL", "1" if use_mkl else "0")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    _write_worker_trace(
        worker_fault_file,
        f"worker start model={model_size} device={device} compute_type={compute_type} cache_dir={model_cache_dir}",
    )
    _write_worker_trace(
        worker_fault_file,
        f"runtime python={sys.version.split()[0]} platform={platform.platform()} arch={platform.machine()} pid={os.getpid()}",
    )

    for pkg in ("faster-whisper", "ctranslate2", "numpy", "huggingface-hub"):
        try:
            ver = metadata.version(pkg)
            _write_worker_trace(worker_fault_file, f"package {pkg}={ver}")
        except Exception:
            _write_worker_trace(worker_fault_file, f"package {pkg}=<not-installed-or-unresolved>")

    for key in ("OMP_NUM_THREADS", "KMP_DUPLICATE_LIB_OK", "CT2_USE_MKL", "HF_HOME", "HF_HUB_DISABLE_SYMLINKS_WARNING"):
        _write_worker_trace(worker_fault_file, f"env {key}={os.getenv(key, '<unset>')}")

    fault_fp = worker_fault_file.open("a", encoding="utf-8", errors="ignore")
    faulthandler.enable(file=fault_fp, all_threads=True)

    try:
        _write_worker_trace(worker_fault_file, "importing numpy, ctranslate2 and faster_whisper")
        import numpy as np  # type: ignore
        import ctranslate2  # type: ignore  # noqa: F401
        from faster_whisper import WhisperModel  # type: ignore

        _log_ctranslate2_runtime(worker_fault_file)
        _log_windows_loaded_modules(worker_fault_file)

        cache_path = Path(model_cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)

        model_ref: str = model_size
        local_snapshot = _resolve_local_whisper_snapshot(cache_path, model_size)
        if local_snapshot:
            model_ref = local_snapshot
            _write_worker_trace(worker_fault_file, f"using local snapshot: {model_ref}")
        else:
            _write_worker_trace(worker_fault_file, f"using remote model id: {model_ref}")

        _write_worker_trace(worker_fault_file, "initializing WhisperModel")
        model = WhisperModel(
            model_ref,
            device=device,
            compute_type=compute_type,
            download_root=str(cache_path),
            cpu_threads=cpu_threads,
            num_workers=num_workers,
        )
        _write_worker_trace(worker_fault_file, "WhisperModel ready")
        result_queue.put({"type": "ready"})
    except Exception as exc:
        _write_worker_trace(worker_fault_file, f"init exception: {exc}")
        _write_worker_trace(worker_fault_file, traceback.format_exc())
        result_queue.put({"type": "init_error", "error": str(exc)})
        return

    while True:
        item = task_queue.get()
        if item is None:
            break

        job_id = item.get("job_id")
        audio_chunk = item.get("audio_chunk", b"")

        try:
            pcm = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
            segments, _ = model.transcribe(pcm, language=language, vad_filter=True)
            text = " ".join(seg.text.strip() for seg in segments if seg.text and seg.text.strip()).strip()
            result_queue.put({"type": "result", "job_id": job_id, "text": text})
        except Exception as exc:
            _write_worker_trace(worker_fault_file, f"transcribe exception: {exc}")
            result_queue.put({"type": "result", "job_id": job_id, "text": "", "error": str(exc)})

    _write_worker_trace(worker_fault_file, "worker shutdown")
    fault_fp.close()
