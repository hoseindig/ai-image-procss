"""Download OpenCV Zoo YuNet weights. Does not run at application startup.

From the project root:

    python scripts/download_models.py

The application never downloads models by itself. If the file is missing, startup
fails with a clear path error.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEST = PROJECT_ROOT / "models" / "face" / "yunet" / "2023mar.onnx"
SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
EXPECTED_SIZE = 232589
URLS = (
    "https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx",
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
)
USER_AGENT = "local-face-camera/0.1 (YuNet 2023mar download)"


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
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".onnx.partial")
    tmp.write_bytes(data)
    tmp.replace(dest)


def main() -> int:
    if DEST.is_file() and _sha256(DEST) == SHA256 and DEST.stat().st_size == EXPECTED_SIZE:
        print(f"Already present: {DEST}")
        return 0
    last_error: str | None = None
    for url in URLS:
        print(f"Downloading {url}")
        try:
            _download(url, DEST)
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            last_error = str(exc)
            print(f"Failed: {exc}")
            continue
        digest = _sha256(DEST)
        size = DEST.stat().st_size
        if digest != SHA256 or size != EXPECTED_SIZE:
            DEST.unlink(missing_ok=True)
            last_error = f"checksum/size mismatch sha256={digest} size={size}"
            print(last_error)
            continue
        print(f"Saved {DEST} ({size} bytes)")
        print(f"SHA-256 {digest}")
        return 0
    print("Could not download YuNet 2023mar.onnx.", file=sys.stderr)
    if last_error:
        print(last_error, file=sys.stderr)
    print("Download the official file manually and place it at:", file=sys.stderr)
    print(f"  {DEST}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
