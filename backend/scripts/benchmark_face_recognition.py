"""CPU benchmark for gallery cosine recognition (in-memory scan).

From the backend directory:

    .\\.venv\\Scripts\\python.exe scripts/benchmark_face_recognition.py
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
    from app.persons.embedding_codec import EMBEDDING_DIM
    from app.vision.embedder import FaceEmbedding
    from app.vision.gallery_recognizer import (
        GalleryEntry,
        GalleryFaceRecognizer,
        InMemoryGalleryStore,
    )
except ModuleNotFoundError as exc:
    print(f"Missing dependency: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc


def _unit(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    vector = rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
    return vector / float(np.linalg.norm(vector))


def _build_gallery(size: int) -> InMemoryGalleryStore:
    entries: list[GalleryEntry] = []
    for index in range(size):
        person_id = f"person-{index // 2}"
        entries.append(
            GalleryEntry(
                person_id=person_id,
                display_name=f"Person {index // 2}",
                enrollment_id=f"enroll-{index}",
                vector=_unit(index + 1),
            )
        )
    return InMemoryGalleryStore(entries)


def _bench(size: int, repeats: int, warmup: int) -> None:
    store = _build_gallery(size)
    recognizer = GalleryFaceRecognizer(store, threshold=0.363)
    query = FaceEmbedding(
        vector=_unit(9999),
        dimension=EMBEDDING_DIM,
        source_track_id=1,
        normalized=True,
    )
    for _ in range(warmup):
        recognizer.recognize(query)
    started = time.perf_counter()
    for _ in range(repeats):
        recognizer.recognize(query)
    elapsed = time.perf_counter() - started
    avg_ms = (elapsed / repeats) * 1000.0
    print(
        f"gallery_samples={size} comparisons_per_query={size} "
        f"repeats={repeats} avg_ms={avg_ms:.4f} "
        f"throughput={repeats / elapsed:.1f} recognitions/sec"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark gallery face recognition")
    parser.add_argument("--repeats", type=int, default=200)
    parser.add_argument("--warmup", type=int, default=20)
    args = parser.parse_args()
    print("GalleryFaceRecognizer (in-memory cosine scan; not full webcam pipeline)")
    for size in (10, 100, 500):
        _bench(size, repeats=args.repeats, warmup=args.warmup)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
