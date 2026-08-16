"""Manual USB webcam smoke test with YuNet overlay. Requires a physical camera.

Run from the backend directory with the virtualenv Python:

    .\\.venv\\Scripts\\python.exe scripts/test_webcam.py
    .\\.venv\\Scripts\\python.exe scripts/test_webcam.py --show-aligned

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
    from app.vision.align import AlignedFace
    from app.vision.exceptions import ModelNotFoundError, VisionError
    from app.vision.factory import (
        create_face_aligner,
        create_face_detector,
        create_face_embedder,
        create_face_quality_assessor,
        create_face_tracker,
    )
    from app.vision.types import (
        EmbeddingInfo,
        EmbeddingSkipReason,
        EmbeddingStatus,
        FaceDetection,
        FaceQuality,
        FaceTrack,
    )
    from app.vision.visualize import compose_aligned_debug, draw_detections, draw_tracks
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
    parser.add_argument(
        "--show-aligned",
        action="store_true",
        help="Show real FaceAligner 112x112 crop beside the camera preview",
    )
    parser.add_argument(
        "--show-embedding",
        action="store_true",
        help="Run SFace and overlay Embedding: 128-D metadata (not the raw vector)",
    )
    parser.add_argument(
        "--log-quality",
        action="store_true",
        help="Print per-track quality metrics when a detection pass runs",
    )
    parser.add_argument(
        "--guided-verify",
        action="store_true",
        help="Timed Phase 5 manual checks (normal / far / dark / motion) with prompts",
    )
    args = parser.parse_args()

    if args.guided_verify:
        args.show_aligned = True
        args.log_quality = True
        # Timed phases own the duration; do not stop early on --frames.
        args.frames = 0

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
    last_tracks: list[FaceTrack] = []
    last_qualities: list[FaceQuality] = []
    last_embeddings: list[EmbeddingInfo] = []
    last_aligned_faces: list[AlignedFace] = []
    last_detect_at = 0.0
    interval_s = settings.face_detection_inference_interval_ms / 1000.0
    tracker = create_face_tracker(settings) if detector is not None else None
    quality_assessor = create_face_quality_assessor(settings) if detector is not None else None
    aligner = create_face_aligner(settings) if detector is not None else None
    embedder = None
    if detector is not None and (args.show_embedding or settings.face_embedding_enabled):
        try:
            embedder = create_face_embedder(settings)
        except (ModelNotFoundError, VisionError) as exc:
            if args.show_embedding:
                message = exc.message if isinstance(exc, VisionError) else str(exc)
                print(message, file=sys.stderr)
                return 1
            embedder = None
    phase_stats: dict[str, dict[str, int]] = {
        "A": {"seen": 0, "accepted": 0, "aligned": 0, "rejected": 0},
        "B": {"seen": 0, "accepted": 0, "aligned": 0, "rejected": 0},
        "C": {"seen": 0, "accepted": 0, "aligned": 0, "rejected": 0},
        "D": {"seen": 0, "accepted": 0, "aligned": 0, "rejected": 0},
    }
    reason_counts: dict[str, dict[str, int]] = {key: {} for key in phase_stats}
    track_ids_seen: set[int] = set()
    if args.show_aligned and aligner is None:
        print(
            "--show-aligned requires FACE_ALIGNMENT_ENABLED=true and a working aligner.",
            file=sys.stderr,
        )
        return 1
    if args.show_embedding and embedder is None:
        print(
            "--show-embedding requires FACE_EMBEDDING_ENABLED=true and SFace installed.",
            file=sys.stderr,
        )
        return 1
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
                f"interval_ms={settings.face_detection_inference_interval_ms} "
                f"tracking={tracker is not None} "
                f"quality={quality_assessor is not None} "
                f"alignment={aligner is not None} "
                f"embedding={embedder is not None} "
                f"show_aligned={args.show_aligned} "
                f"show_embedding={args.show_embedding}"
            )
        source.start()
        if display:
            import cv2

            cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        last_frame_at = None
        started = time.perf_counter()
        phase_started = started
        phase_index = 0
        phase_labels = (
            "A NORMAL: frontal face, good lighting — hold still",
            "B FAR: move farther from the camera",
            "C DARK: reduce light / shade face",
            "D MOTION: move head quickly side to side",
        )
        phase_seconds = 12.0
        if args.guided_verify:
            print("=" * 60)
            print("GUIDED PHASE 5 MANUAL VERIFY")
            print(f"Phase {phase_labels[0]}")
            print("Press Q anytime to abort. Camera releases on exit.")
            print("=" * 60)
        while True:
            if args.guided_verify:
                phase_elapsed = time.perf_counter() - phase_started
                if phase_elapsed >= phase_seconds and phase_index < len(phase_labels) - 1:
                    phase_index += 1
                    phase_started = time.perf_counter()
                    print("=" * 60)
                    print(f"Phase {phase_labels[phase_index]}")
                    print("=" * 60)
            frame = source.read()
            if frame is None:
                time.sleep(0.01)
                continue
            if last_frame_at is not None and frame.timestamp == last_frame_at:
                time.sleep(0.01)
                continue
            last_frame_at = frame.timestamp
            captured += 1
            now = time.monotonic()
            if detector is not None and now - last_detect_at >= interval_s:
                last_faces = detector.detect(frame)
                last_tracks = tracker.update(last_faces) if tracker is not None else []
                last_qualities = []
                last_aligned_faces = []
                last_embeddings = []
                if quality_assessor is not None:
                    for track in last_tracks:
                        if track.missed_frames != 0:
                            continue
                        quality = quality_assessor.assess(frame, track)
                        last_qualities.append(quality)
                        if aligner is not None and quality.accepted:
                            last_aligned_faces.append(aligner.align(frame, track))
                elif aligner is not None:
                    for track in last_tracks:
                        if track.missed_frames != 0:
                            continue
                        last_aligned_faces.append(aligner.align(frame, track))
                if embedder is not None:
                    aligned_by_id = {item.source_track_id: item for item in last_aligned_faces}
                    rejected = {item.track_id for item in last_qualities if not item.accepted}
                    for track in last_tracks:
                        if track.missed_frames != 0:
                            continue
                        if track.track_id in rejected:
                            last_embeddings.append(
                                EmbeddingInfo(
                                    track_id=track.track_id,
                                    status=EmbeddingStatus.SKIPPED,
                                    reason=EmbeddingSkipReason.QUALITY_REJECTED,
                                )
                            )
                            continue
                        aligned_face = aligned_by_id.get(track.track_id)
                        if aligned_face is None:
                            last_embeddings.append(
                                EmbeddingInfo(
                                    track_id=track.track_id,
                                    status=EmbeddingStatus.SKIPPED,
                                    reason=EmbeddingSkipReason.ALIGNMENT_UNAVAILABLE,
                                )
                            )
                            continue
                        embedding = embedder.embed(aligned_face)
                        last_embeddings.append(
                            EmbeddingInfo(
                                track_id=track.track_id,
                                status=EmbeddingStatus.GENERATED,
                                dimension=embedding.dimension,
                                normalized=embedding.normalized,
                            )
                        )
                last_detect_at = now
                detected_frames += 1
                if args.log_quality and last_tracks:
                    prefix = f"P{phase_labels[phase_index][0]} " if args.guided_verify else ""
                    _log_quality_pass(last_tracks, last_qualities, last_aligned_faces, prefix)
                    for info in last_embeddings:
                        print(
                            f"{prefix}embed track=#{info.track_id} status={info.status.value} "
                            f"dim={info.dimension} reason={info.reason}"
                        )
                if args.guided_verify and last_qualities:
                    phase_key = phase_labels[phase_index][0]
                    for quality in last_qualities:
                        phase_stats[phase_key]["seen"] += 1
                        track_ids_seen.add(quality.track_id)
                        if quality.accepted:
                            phase_stats[phase_key]["accepted"] += 1
                        else:
                            phase_stats[phase_key]["rejected"] += 1
                            for reason in quality.reasons:
                                bucket = reason_counts[phase_key]
                                bucket[reason.value] = bucket.get(reason.value, 0) + 1
                    phase_stats[phase_key]["aligned"] += len(last_aligned_faces)
            elapsed = max(time.perf_counter() - started, 1e-6)
            fps = captured / elapsed
            if display:
                import cv2

                if detector is not None and tracker is not None:
                    image = draw_tracks(frame.data, last_tracks, last_qualities, last_embeddings)
                elif detector is not None:
                    image = draw_detections(frame.data, last_faces)
                else:
                    image = frame.data
                if args.show_aligned:
                    image = compose_aligned_debug(image, last_aligned_faces)
                overlay = (
                    f"fps={fps:.1f} faces={len(last_faces)} "
                    f"tracks={len(last_tracks)} aligned={len(last_aligned_faces)} "
                    f"embedded="
                    f"{sum(1 for item in last_embeddings if item.status.value == 'generated')} "
                    f"{frame.width}x{frame.height}"
                )
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
                if args.guided_verify:
                    cv2.putText(
                        image,
                        phase_labels[phase_index][:48],
                        (8, 48),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (0, 200, 255),
                        1,
                        cv2.LINE_AA,
                    )
                cv2.imshow(window, image)
                pressed = cv2.waitKey(1) & 0xFF
                if pressed in {ord("q"), ord("Q"), 27}:
                    break
            elif captured % 10 == 0:
                accepted = sum(1 for item in last_qualities if item.accepted)
                print(
                    f"frames={captured} fps={fps:.1f} size={frame.width}x{frame.height} "
                    f"faces={len(last_faces)} tracks={len(last_tracks)} "
                    f"quality_ok={accepted} aligned={len(last_aligned_faces)} "
                    f"ids={[track.track_id for track in last_tracks]}"
                )
            if args.frames > 0 and captured >= args.frames:
                break
            if args.guided_verify:
                total_guided = phase_seconds * len(phase_labels)
                if time.perf_counter() - started >= total_guided:
                    break
        elapsed = max(time.perf_counter() - started, 1e-6)
        print(
            f"Captured {captured} frames, ~{captured / elapsed:.1f} FPS, "
            f"detection passes={detected_frames}"
        )
        if args.guided_verify:
            print("Guided verify summary:")
            print(f"  unique track ids observed: {sorted(track_ids_seen)}")
            for phase_name in ("A", "B", "C", "D"):
                stats = phase_stats[phase_name]
                reasons = reason_counts[phase_name]
                print(
                    f"  Phase {phase_name}: seen={stats['seen']} accepted={stats['accepted']} "
                    f"rejected={stats['rejected']} aligned={stats['aligned']} "
                    f"reasons={reasons or '-'}"
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


def _log_quality_pass(
    tracks: list[FaceTrack],
    qualities: list[FaceQuality],
    aligned: list[AlignedFace],
    prefix: str = "",
) -> None:
    quality_by_id = {item.track_id: item for item in qualities}
    aligned_ids = {item.source_track_id for item in aligned}
    for track in tracks:
        if track.missed_frames != 0:
            continue
        quality = quality_by_id.get(track.track_id)
        box = track.bounding_box
        if quality is None:
            print(
                f"{prefix}track=#{track.track_id} conf={track.confidence:.2f} "
                f"size={box.width:.0f}x{box.height:.0f} quality=n/a"
            )
            continue
        reasons = ",".join(reason.value for reason in quality.reasons) or "-"
        sharp = f"{quality.sharpness:.1f}" if quality.sharpness is not None else "n/a"
        bright = f"{quality.brightness:.1f}" if quality.brightness is not None else "n/a"
        print(
            f"{prefix}track=#{track.track_id} conf={track.confidence:.2f} "
            f"size={box.width:.0f}x{box.height:.0f} "
            f"accepted={quality.accepted} reasons={reasons} "
            f"sharp={sharp} bright={bright} "
            f"aligned={track.track_id in aligned_ids}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
