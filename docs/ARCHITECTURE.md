# Architecture (Phase 5)

Phase 5 adds face quality assessment and five-point alignment on top of tracking. Recognition, events, and the frontend are still absent.

## Runtime (current)

```text
USB Webcam
    → CameraSource (UsbCameraSource)
    → CameraManager (latest-frame slot)
    → DetectionWorker (interval, latest-result slot)
    → FaceDetector
          └── YuNetFaceDetector
                └── InferenceEngine (OnnxRuntimeEngine, CPUExecutionProvider)
    → FaceDetection[]
    → FaceTracker
          └── IoUCentroidFaceTracker
    → FaceTrack[]
    → FaceQualityAssessor
          └── HeuristicFaceQualityAssessor
    → FaceQuality[]  (accepted / reasons / metrics)
    → FaceAligner
          └── LandmarkFaceAligner
    → AlignedFace[]  (112×112 default crop; size-1 slot, not queued)
    → visualization (preview only)
    → REST (detections / tracks / quality metadata)
```

`FaceDetector` does not know about tracking, quality, or alignment. Quality and alignment do not know about YuNet or future SFace inference.

## Protocols

```text
FaceTracker.update(detections) → list[FaceTrack]
FaceQualityAssessor.assess(frame, track) → FaceQuality
FaceAligner.align(frame, track) → AlignedFace
```

Future embedding should consume `AlignedFace` without rewriting these stages:

```text
AlignedFace → FaceEmbedder → Embedding
```

## Latest-frame scheduling

Unchanged size-1 slots:

```text
Camera thread     → LatestFrameSlot (size 1)
Detection thread  → detect → track → quality → align
                  → LatestValueSlot[DetectionSnapshot] (size 1)
                  → LatestValueSlot[AlignedFace…] (size 1)
```

No frame queue. Quality and alignment run on the same worker thread as detection.

## Layout

```text
backend/
  app/
    cameras/
    vision/              # detector, tracker, quality, align, worker
    services/detection.py
  scripts/test_webcam.py
  scripts/benchmark_face_detection.py
  scripts/benchmark_face_tracking.py
  scripts/benchmark_face_quality.py
```

## API

| Method | Path | Role |
| --- | --- | --- |
| GET | `/api/health` | Liveness |
| GET | `/api/system/status` | Adds `quality_enabled` / `alignment_enabled` |
| GET | `/api/cameras` | Registered cameras |
| GET | `/api/cameras/{id}` | One camera |
| POST | `/api/cameras/{id}/start` | Open + capture + attach worker |
| POST | `/api/cameras/{id}/stop` | Detach worker + stop + release |
| GET | `/api/cameras/{id}/detections` | `faces`, `tracks` (+ optional `quality`), timings |

Aligned pixel buffers are not returned over REST. See `docs/FACE_QUALITY.md` and `docs/TRACKING.md`.
