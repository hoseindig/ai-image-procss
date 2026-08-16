"""Download OpenCV Zoo YuNet + SFace weights. Does not run at application startup.

From the project root:

    python scripts/download_models.py

The application never downloads models by itself. If a required file is missing,
startup fails with a clear path error.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "local-face-camera/0.1 (OpenCV Zoo model download)"


@dataclass(frozen=True)
class ModelSpec:
    name: str
    dest: Path
    sha256: str
    expected_size: int
    urls: tuple[str, ...]


MODELS = (
    ModelSpec(
        name="YuNet 2023mar",
        dest=PROJECT_ROOT / "models" / "face" / "yunet" / "2023mar.onnx",
        sha256="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
        expected_size=232589,
        urls=(
            "https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx",
            "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        ),
    ),
    ModelSpec(
        name="SFace 2021dec",
        dest=PROJECT_ROOT / "models" / "face" / "sface" / "2021dec.onnx",
        sha256="0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
        expected_size=38696353,
        urls=(
            "https://huggingface.co/opencv/face_recognition_sface/resolve/main/face_recognition_sface_2021dec.onnx",
            "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        ),
    ),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, dest: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".onnx.partial")
    tmp.write_bytes(data)
    tmp.replace(dest)


def _ensure(spec: ModelSpec) -> int:
    if (
        spec.dest.is_file()
        and _sha256(spec.dest) == spec.sha256
        and spec.dest.stat().st_size == spec.expected_size
    ):
        print(f"Already present: {spec.dest}")
        return 0
    last_error: str | None = None
    for url in spec.urls:
        print(f"Downloading {spec.name}: {url}")
        try:
            _download(url, spec.dest)
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            last_error = str(exc)
            print(f"Failed: {exc}")
            continue
        digest = _sha256(spec.dest)
        size = spec.dest.stat().st_size
        if digest != spec.sha256 or size != spec.expected_size:
            spec.dest.unlink(missing_ok=True)
            last_error = f"checksum/size mismatch sha256={digest} size={size}"
            print(last_error)
            continue
        checksums = spec.dest.parent / "SHA256SUMS"
        checksums.write_text(f"{digest}  {spec.dest.name}\n", encoding="utf-8")
        print(f"Saved {spec.dest} ({size} bytes)")
        print(f"SHA-256 {digest}")
        return 0
    print(f"Could not download {spec.name}.", file=sys.stderr)
    if last_error:
        print(last_error, file=sys.stderr)
    print("Download the official file manually and place it at:", file=sys.stderr)
    print(f"  {spec.dest}", file=sys.stderr)
    return 1


def main() -> int:
    failures = 0
    for spec in MODELS:
        failures += _ensure(spec)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
