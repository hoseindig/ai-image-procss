"""Manual USB webcam smoke test with YuNet overlay. Requires a physical camera.

Run from the backend directory with the virtualenv Python:

    .\\.venv\\Scripts\\python.exe scripts/test_webcam.py

Press Q in the preview window to exit. The camera is released on exit.
Face boxes are drawn by visualization code, not by the detector itself.
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
    from app.cameras.manager import config_from_settings
    from app.cameras.usb import UsbCameraSource
    from app.core.config import load_settings
    from app.core.logging import setup_logging
    from app.vision.exceptions import ModelNotFoundError, VisionError
    from app.vision.factory import create_face_detector
    from app.vision.types import FaceDetection
    from app.vision.visualize import draw_detections
except ModuleNotFoundError as exc:
    venv_python = _venv_python()
    print("Missing dependency while starting the webcam smoke test.", file=sys.stderr)
    if venv_python is not None:
        print("Use the backend virtualenv Python, for example:", file=sys.stderr)
        print(f"  {venv_python} scripts/test_webcam.py", file=sys.stderr)
    print(f"Original error: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="USB webcam smoke test")
    parser.add_argument("--index", type=int, default=None, help="Device index (default: settings)")
    parser.add_argument("--width", type=int, default=None)
    parser.add_argument("--height", type=int, default=None)
    parser.add_argument("--fps", type=float, default=None)
    parser.add_argument(
        "--frames", type=int, default=0, help="Capture N frames then exit (0 = until Q)"
    )
    parser.add_argument("--no-display", action="store_true", help="Do not open a preview window")
    parser.add_argument(
        "--no-detect",
        action="store_true",
        help="Skip YuNet overlay (camera-only, Phase 2 behavior)",
    )
    args = parser.parse_args()

    settings = load_settings()
    setup_logging(settings.log_level)
    config = config_from_settings(settings)
    if args.index is not None:
        config = config.model_copy(update={"device_index": args.index})
    if args.width is not None:
        config = config.model_copy(update={"width": args.width})
    if args.height is not None:
        config = config.model_copy(update={"height": args.height})
    if args.fps is not None:
        config = config.model_copy(update={"fps": args.fps})

    detector = None
    if not args.no_detect:
        try:
            detector = create_face_detector(settings)
        except (ModelNotFoundError, VisionError) as exc:
            message = exc.message if isinstance(exc, VisionError) else str(exc)
            print(message, file=sys.stderr)
            print("Install the model with: python scripts/download_models.py", file=sys.stderr)
            print("Or pass --no-detect for a camera-only preview.", file=sys.stderr)
            return 1

    source = UsbCameraSource(config)
    display = not args.no_display
    window = "webcam-smoke-test"
    captured = 0
    detected_frames = 0
    last_faces: list[FaceDetection] = []
    last_detect_at = 0.0
    interval_s = settings.face_detection_inference_interval_ms / 1000.0
    started = time.perf_counter()
    try:
        source.open()
        status = source.get_status()
        print(
            f"Opened index={status.device_index} "
            f"actual={status.width}x{status.height}@{status.fps:.1f} "
            f"(requested {config.width}x{config.height}@{config.fps})"
        )
        if detector is not None:
            print(
                f"YuNet provider={detector.provider} "
                f"input={detector.config.input_width}x{detector.config.input_height} "
                f"interval_ms={settings.face_detection_inference_interval_ms}"
            )
        source.start()
        if display:
            import cv2

            cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        while True:
            frame = source.read()
            if frame is None:
                time.sleep(0.01)
                continue
            captured += 1
            now = time.monotonic()
            if detector is not None and now - last_detect_at >= interval_s:
                last_faces = detector.detect(frame)
                last_detect_at = now
                detected_frames += 1
            elapsed = max(time.perf_counter() - started, 1e-6)
            fps = captured / elapsed
            if display:
                import cv2

                image = (
                    draw_detections(frame.data, last_faces) if detector is not None else frame.data
                )
                overlay = f"fps={fps:.1f} faces={len(last_faces)} {frame.width}x{frame.height}"
                cv2.putText(
                    image,
                    overlay,
                    (8, 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
                cv2.imshow(window, image)
                key = cv2.waitKey(1) & 0xFF
                if key in {ord("q"), ord("Q"), 27}:
                    break
            elif captured % 10 == 0:
                print(
                    f"frames={captured} fps={fps:.1f} size={frame.width}x{frame.height} "
                    f"faces={len(last_faces)}"
                )
            if args.frames > 0 and captured >= args.frames:
                break
        elapsed = max(time.perf_counter() - started, 1e-6)
        print(
            f"Captured {captured} frames, ~{captured / elapsed:.1f} FPS, "
            f"detection passes={detected_frames}"
        )
        return 0
    except Exception as exc:
        print(f"Webcam smoke test failed: {exc}")
        return 1
    finally:
        source.close()
        if display:
            try:
                import cv2

                cv2.destroyAllWindows()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
