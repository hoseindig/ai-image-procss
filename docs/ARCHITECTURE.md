# Architecture (Phase 6)

Phase 6 adds SFace embedding after quality-accepted alignment. Recognition, person IDs, and the frontend are still absent.

## Runtime (current)

```text
USB Webcam
    → CameraSource
    → CameraManager (latest-frame slot)
    → DetectionWorker (interval, latest-result slot)
    → FaceDetector (YuNet)
    → FaceTracker (IoU)
    → FaceQualityAssessor
    → FaceAligner (5-point)
    → FaceEmbedder (SFaceEmbedder / ONNX Runtime CPU)
    → FaceEmbedding (128-D, L2-normalized; size-1 slot)
    → visualization / REST metadata
```

Application code depends on `FaceEmbedder`, not ONNX Runtime.

## Latest-frame scheduling

```text
Camera thread     → LatestFrameSlot (size 1)
Detection thread  → detect → track → quality → align → embed
                  → LatestValueSlot[DetectionSnapshot] (size 1)
                  → LatestValueSlot[AlignedFace…] (size 1)
                  → LatestValueSlot[FaceEmbedding…] (size 1)
```

No unbounded queues. One SFace session is loaded once and reused.

## API

| Method | Path | Role |
| --- | --- | --- |
| GET | `/api/cameras/{id}/detections` | faces, tracks, quality, embedding **metadata** |

Raw embedding vectors are not exposed on the normal API.

## Docs

- `docs/FACE_EMBEDDING.md` — model, preprocessing, privacy
- `docs/FACE_QUALITY.md` — quality / alignment
- `docs/TRACKING.md` — Track ID semantics
- `docs/MODELS.md` — licenses and checksums
