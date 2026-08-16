# Architecture (Phase 7A)

Phase 7A adds persistent **Person** records and an embedding **gallery**. Recognition / matching are still absent.

## Runtime (vision)

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

## Persistence (enrollment)

```text
Validated FaceEmbedding + quality.accepted
    → EnrollmentService
    → SQLite enrollment_samples (binary float32 blob)
PersonService → SQLite persons (UUID Person ID)
```

Application enrollment code does **not** call ONNX Runtime directly. Track ID is optional tracing metadata on a sample — never a Person ID.

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
| POST/GET/PATCH/DELETE | `/api/persons…` | person CRUD + soft deactivate |
| POST/GET/DELETE | `/api/persons/{id}/enrollments…` | gallery samples (POST accepts vector; GET does not return it) |

Raw embedding vectors are not exposed on normal GET APIs.

## Docs

- `docs/PERSON_ENROLLMENT.md` — schema, storage format, privacy, backup
- `docs/FACE_EMBEDDING.md` — model, preprocessing
- `docs/FACE_QUALITY.md` — quality / alignment
- `docs/TRACKING.md` — Track ID semantics
- `docs/MODELS.md` — licenses and checksums
