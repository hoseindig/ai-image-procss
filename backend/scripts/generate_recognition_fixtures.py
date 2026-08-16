"""Generate deterministic synthetic 112×112 aligned-face fixtures for recognition tests.

TEST ONLY artifacts. Not photographs of people. Not for production enrollment.

Chosen seeds produce SFace cosine(A,B) < FACE_RECOGNITION_THRESHOLD (0.363)
on the project SFace ONNX (verified when regenerating).

Usage (from repo root, with backend venv):

    python backend/scripts/generate_recognition_fixtures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "backend" / "tests" / "fixtures" / "faces"


def _face_a() -> np.ndarray:
    """Deterministic synthetic crop A (seed 8)."""
    rng = np.random.default_rng(8)
    image = np.zeros((112, 112, 3), dtype=np.uint8)
    image[:, :, 0] = rng.integers(0, 255, size=(112, 112), dtype=np.uint8)
    image[0:56, 0:56] = (255, 255, 255)
    return image


def _face_b() -> np.ndarray:
    """Deterministic synthetic crop B (seed 143) — dissimilar to A under SFace."""
    rng = np.random.default_rng(143)
    image = np.zeros((112, 112, 3), dtype=np.uint8)
    image[:, :, 2] = rng.integers(0, 255, size=(112, 112), dtype=np.uint8)
    image[56:112, 56:112] = (255, 255, 255)
    return (255 - image).astype(np.uint8)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    a_path = OUT / "synthetic_aligned_a.png"
    b_path = OUT / "synthetic_aligned_b.png"
    if not cv2.imwrite(str(a_path), _face_a()):
        print(f"Failed to write {a_path}", file=sys.stderr)
        return 1
    if not cv2.imwrite(str(b_path), _face_b()):
        print(f"Failed to write {b_path}", file=sys.stderr)
        return 1
    print(f"Wrote {a_path}")
    print(f"Wrote {b_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
