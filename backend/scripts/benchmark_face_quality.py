"""CPU baseline for face quality assessment and landmark alignment.

From the backend directory:

    .\\.venv\\Scripts\\python.exe scripts/benchmark_face_quality.py
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
    from app.vision.factory import create_face_aligner, create_face_quality_assessor
    from tests.quality_helpers import textured_frame, track_from_box
except ModuleNotFoundError as exc:
    venv_python = _venv_python()
    print("Missing dependency while starting the face-quality benchmark.", file=sys.stderr)
    if venv_python is not None:
        print(f"  {venv_python} scripts/benchmark_face_quality.py", file=sys.stderr)
    print(f"Original error: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Face quality + alignment CPU benchmark")
    parser.add_argument("--frames", type=int, default=300)
    parser.add_argument("--faces", type=int, default=2)
    parser.add_argument("--warmup", type=int, default=20)
    args = parser.parse_args()

    settings = load_settings()
    setup_logging(settings.log_level)
    assessor = create_face_quality_assessor(settings)
    aligner = create_face_aligner(settings)
    if assessor is None and aligner is None:
        print(
            "Quality and alignment are disabled. "
            "Set FACE_QUALITY_ENABLED and/or FACE_ALIGNMENT_ENABLED.",
            file=sys.stderr,
        )
        return 1

    frame = textured_frame(640, 480, face_box=(80, 60, 140, 140))
    tracks = [
        track_from_box(
            track_id=index + 1,
            x=80.0 + index * 180.0,
            y=60.0,
            width=140.0,
            height=140.0,
        )
        for index in range(args.faces)
    ]
    # Paint additional face boxes for multi-face timing.
    for track in tracks[1:]:
        x = int(track.bounding_box.x)
        y = int(track.bounding_box.y)
        w = int(track.bounding_box.width)
        h = int(track.bounding_box.height)
        if y + h <= frame.height and x + w <= frame.width:
            frame.data[y : y + h, x : x + w] = frame.data[60:200, 80:220]

    for _ in range(max(args.warmup, 0)):
        for track in tracks:
            if assessor is not None:
                quality = assessor.assess(frame, track)
                if aligner is not None and quality.accepted:
                    aligner.align(frame, track)
            elif aligner is not None:
                aligner.align(frame, track)

    quality_latencies: list[float] = []
    align_latencies: list[float] = []
    total_latencies: list[float] = []
    accepted = 0
    aligned = 0

    for _ in range(args.frames):
        total_started = time.perf_counter()
        for track in tracks:
            quality_accepted = True
            if assessor is not None:
                q_started = time.perf_counter()
                quality = assessor.assess(frame, track)
                quality_latencies.append((time.perf_counter() - q_started) * 1000.0)
                quality_accepted = quality.accepted
                if quality.accepted:
                    accepted += 1
            if aligner is not None and quality_accepted:
                a_started = time.perf_counter()
                aligner.align(frame, track)
                align_latencies.append((time.perf_counter() - a_started) * 1000.0)
                aligned += 1
        total_latencies.append((time.perf_counter() - total_started) * 1000.0)

    def _avg(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    print("Quality + alignment benchmark (synthetic textured faces)")
    print(f"Frames: {args.frames} timed + {args.warmup} warmup")
    print(f"Faces per frame: {args.faces}")
    print(f"Accepted assessments: {accepted}")
    print(f"Aligned crops: {aligned}")
    if quality_latencies:
        print(f"Average quality time: {_avg(quality_latencies):.4f} ms")
    else:
        print("Average quality time: n/a (disabled)")
    if align_latencies:
        print(f"Average alignment time: {_avg(align_latencies):.4f} ms")
    else:
        print("Average alignment time: n/a (disabled or none accepted)")
    print(f"Average total per frame: {_avg(total_latencies):.4f} ms")
    fps = args.frames / (sum(total_latencies) / 1000.0) if total_latencies else 0.0
    print(f"Approx pipeline FPS: {fps:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
