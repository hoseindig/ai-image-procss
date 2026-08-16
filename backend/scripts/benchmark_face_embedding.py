"""CPU baseline for SFace embedding. Uses synthetic 112x112 aligned faces.

From the backend directory:

    .\\.venv\\Scripts\\python.exe scripts/benchmark_face_embedding.py
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np

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
    from app.vision.align import AlignedFace
    from app.vision.exceptions import ModelNotFoundError, VisionError
    from app.vision.factory import create_face_embedder
except ModuleNotFoundError as exc:
    venv_python = _venv_python()
    print("Missing dependency while starting the face-embedding benchmark.", file=sys.stderr)
    if venv_python is not None:
        print(f"  {venv_python} scripts/benchmark_face_embedding.py", file=sys.stderr)
    print(f"Original error: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc


def _synthetic_aligned(seed: int) -> AlignedFace:
    rng = np.random.default_rng(seed)
    image = rng.integers(40, 220, size=(112, 112, 3), dtype=np.uint8)
    return AlignedFace(
        image=image,
        width=112,
        height=112,
        source_track_id=1,
        transform=np.eye(2, 3, dtype=np.float64),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="SFace embedding CPU benchmark")
    parser.add_argument("--frames", type=int, default=200)
    parser.add_argument("--warmup", type=int, default=20)
    args = parser.parse_args()

    settings = load_settings()
    setup_logging(settings.log_level)
    init_started = time.perf_counter()
    try:
        embedder = create_face_embedder(settings)
    except (ModelNotFoundError, VisionError) as exc:
        message = exc.message if isinstance(exc, VisionError) else str(exc)
        print(message, file=sys.stderr)
        return 1
    init_ms = (time.perf_counter() - init_started) * 1000.0
    if embedder is None:
        print("Embedding is disabled. Set FACE_EMBEDDING_ENABLED=true.", file=sys.stderr)
        return 1

    for index in range(max(args.warmup, 0)):
        embedder.embed(_synthetic_aligned(index))

    latencies: list[float] = []
    started = time.perf_counter()
    for index in range(args.frames):
        face = _synthetic_aligned(index + 1000)
        infer_started = time.perf_counter()
        result = embedder.embed(face)
        latencies.append((time.perf_counter() - infer_started) * 1000.0)
        assert result.dimension == 128
    elapsed = max(time.perf_counter() - started, 1e-9)
    average_ms = sum(latencies) / len(latencies)
    eps = args.frames / elapsed
    print("Embedder: SFace 2021dec (raw inference on synthetic 112x112 crops)")
    print(f"Model init time: {init_ms:.2f} ms")
    print(f"Frames: {args.frames} timed + {args.warmup} warmup")
    print(f"Average embedding time: {average_ms:.4f} ms")
    print(f"Embeddings/sec: {eps:.1f}")
    print("Note: this is raw SFace latency, not full webcam pipeline latency.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
