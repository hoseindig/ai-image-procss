"""CPU baseline for IoU/centroid face tracking. Uses synthetic detections only.

From the backend directory:

    .\\.venv\\Scripts\\python.exe scripts/benchmark_face_tracking.py
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
    from app.core.config import load_settings
    from app.core.logging import setup_logging
    from app.vision.factory import create_face_tracker
    from app.vision.types import FaceDetection
    from tests.yunet_helpers import sample_face
except ModuleNotFoundError as exc:
    venv_python = _venv_python()
    print("Missing dependency while starting the face-tracking benchmark.", file=sys.stderr)
    if venv_python is not None:
        print(f"  {venv_python} scripts/benchmark_face_tracking.py", file=sys.stderr)
    print(f"Original error: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc


def _frame_detections(frame_index: int, face_count: int) -> list[FaceDetection]:
    detections: list[FaceDetection] = []
    for index in range(face_count):
        x = 20.0 + index * 140.0 + (frame_index % 8) * 3.0
        y = 30.0 + index * 12.0
        detections.append(sample_face(x=x, y=y, width=48, height=56, confidence=0.9 - index * 0.02))
    return detections


def main() -> int:
    parser = argparse.ArgumentParser(description="IoU face-tracking CPU benchmark")
    parser.add_argument("--frames", type=int, default=500)
    parser.add_argument("--faces", type=int, default=4)
    parser.add_argument("--warmup", type=int, default=20)
    args = parser.parse_args()

    settings = load_settings()
    setup_logging(settings.log_level)
    tracker = create_face_tracker(settings)
    if tracker is None:
        print("Tracking is disabled. Set FACE_TRACKING_ENABLED=true.", file=sys.stderr)
        return 1

    for index in range(max(args.warmup, 0)):
        tracker.update(_frame_detections(index, args.faces))

    started = time.perf_counter()
    latencies: list[float] = []
    last_count = 0
    for index in range(args.frames):
        detections = _frame_detections(index + args.warmup, args.faces)
        infer_started = time.perf_counter()
        tracks = tracker.update(detections)
        latencies.append((time.perf_counter() - infer_started) * 1000.0)
        last_count = len(tracks)
    elapsed = max(time.perf_counter() - started, 1e-9)
    average_ms = sum(latencies) / len(latencies)
    fps = args.frames / elapsed
    print("Tracker: IoU + centroid")
    print(f"Frames: {args.frames} timed + {args.warmup} warmup")
    print(f"Synthetic faces per frame: {args.faces}")
    print(f"Tracks at end: {last_count}")
    print(f"Average update time: {average_ms:.4f} ms")
    print(f"Tracker FPS: {fps:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
