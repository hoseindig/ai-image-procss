"""CPU baseline for YuNet face detection. Requires the local ONNX file.

From the backend directory:

    .\\.venv\\Scripts\\python.exe scripts/benchmark_face_detection.py
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


def _venv_python() -> Path | None:
    if sys.platform == "win32":
        candidate = _BACKEND_ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = _BACKEND_ROOT / ".venv" / "bin" / "python"
    return candidate if candidate.is_file() else None


def _reexec_with_venv_if_needed() -> None:
    venv_python = _venv_python()
    if venv_python is None:
        return
    current = Path(sys.executable).resolve()
    target = venv_python.resolve()
    if current == target:
        return
    os.execv(str(target), [str(target), *sys.argv])


_reexec_with_venv_if_needed()

try:
    from datetime import UTC, datetime

    import numpy as np

    from app.cameras.types import Frame
    from app.core.config import load_settings
    from app.core.logging import setup_logging
    from app.vision.exceptions import ModelNotFoundError
    from app.vision.factory import create_face_detector
except ModuleNotFoundError as exc:
    venv_python = _venv_python()
    print("Missing dependency while starting the face-detection benchmark.", file=sys.stderr)
    if venv_python is not None:
        print(f"  {venv_python} scripts/benchmark_face_detection.py", file=sys.stderr)
    print(f"Original error: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc


def _blank_frame(width: int, height: int, fill: int = 32) -> Frame:
    data = np.full((height, width, 3), fill, dtype=np.uint8)
    return Frame(data=data, timestamp=datetime.now(UTC), width=width, height=height)


def _rss_bytes() -> int | None:
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        try:
            counters = ProcessMemoryCounters()
            counters.cb = ctypes.sizeof(ProcessMemoryCounters)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            get_info = psapi.GetProcessMemoryInfo
            get_info.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(ProcessMemoryCounters),
                wintypes.DWORD,
            ]
            get_info.restype = wintypes.BOOL
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            if not get_info(handle, ctypes.byref(counters), counters.cb):
                return None
            return int(counters.WorkingSetSize)
        except Exception:
            return None
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform == "darwin":
            return int(usage)
        return int(usage) * 1024
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="YuNet CPU detection benchmark")
    parser.add_argument("--frames", type=int, default=50, help="Timed inference iterations")
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args()

    settings = load_settings()
    setup_logging(settings.log_level)
    try:
        detector = create_face_detector(settings)
    except ModelNotFoundError as exc:
        print(exc.message, file=sys.stderr)
        print("Install the model with: python scripts/download_models.py", file=sys.stderr)
        return 1

    frame = _blank_frame(args.width, args.height, fill=32)
    for _ in range(max(args.warmup, 0)):
        detector.detect(frame)

    rss_before = _rss_bytes()
    started = time.perf_counter()
    latencies: list[float] = []
    detections = 0
    for _ in range(args.frames):
        infer_started = time.perf_counter()
        faces = detector.detect(frame)
        latencies.append((time.perf_counter() - infer_started) * 1000.0)
        detections += len(faces)
    elapsed = max(time.perf_counter() - started, 1e-9)
    rss_after = _rss_bytes()
    average_ms = sum(latencies) / len(latencies)
    fps = args.frames / elapsed
    print("Model: YuNet 2023mar.onnx")
    print(f"Provider: {detector.provider}")
    print(f"Input: {detector.config.input_width}x{detector.config.input_height}")
    print(f"Frame: {args.width}x{args.height} (blank, {args.frames} timed + {args.warmup} warmup)")
    print(f"Faces detected (sum over timed frames): {detections}")
    print(f"Average inference time: {average_ms:.2f} ms")
    print(f"Detection FPS: {fps:.2f}")
    if rss_before is not None and rss_after is not None:
        print(f"RSS before: {rss_before / (1024 * 1024):.1f} MB")
        print(f"RSS after: {rss_after / (1024 * 1024):.1f} MB")
        print(f"RSS delta: {(rss_after - rss_before) / (1024 * 1024):.1f} MB")
    else:
        print("Memory: unavailable on this platform helper")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
