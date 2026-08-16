# Architecture (Phase 7B)

Phase 7B adds local CPU gallery recognition after SFace embedding. Events, snapshots, and the frontend remain absent.

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
    → FaceEmbedding (128-D, L2-normalized)
    → FaceRecognizer (GalleryFaceRecognizer / cosine)
    → RecognitionResult
    → visualization / REST metadata
```

## Persistence

```text
Person + EnrollmentSample (SQLite)
    ← EnrollmentService (Phase 7A)
    → SqlAlchemyGalleryStore (active persons only)
    → GalleryFaceRecognizer
```

Application code depends on `FaceRecognizer`, not ONNX Runtime. Track ID is runtime tracing only.

## Latest-frame scheduling

Bounded size-1 slots for frame, detection snapshot, aligned faces, and embeddings. One YuNet session and one SFace session are reused. Gallery is loaded per recognition call via a single join query (no N+1).

## API

| Method | Path | Role |
| --- | --- | --- |
| GET | `/api/cameras/{id}/detections` | faces, tracks, quality, embedding metadata, **recognition** |
| POST/GET/PATCH/DELETE | `/api/persons…` | person + enrollment gallery |

Raw embedding vectors are never exposed on normal GET APIs. Similarity is not a percentage.

## Docs

- `docs/FACE_RECOGNITION.md` — matching, threshold, privacy, security limits
- `docs/PERSON_ENROLLMENT.md` — gallery persistence
- `docs/FACE_EMBEDDING.md` — SFace model / preprocessing
- `docs/MODELS.md` — licenses and checksums
