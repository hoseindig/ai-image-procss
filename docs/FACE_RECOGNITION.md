# Face recognition (Phase 7B)

Phase 7B compares a live **128-D L2-normalized SFace embedding** to the SQLite enrollment gallery using **cosine similarity**. It identifies a persistent Person or returns **unknown**. It is a **local** face recognition system — not production-grade biometric authentication.

**Track ID ≠ Person ID.**

## Architecture

```text
FaceEmbedding
    → FaceRecognizer (GalleryFaceRecognizer)
    → RecognitionResult (matched | unknown | skipped | error)
```

Per person score = **maximum** cosine similarity across that person's enrollment samples (no averaging). Best person = highest person score. Match when:

```text
best_similarity >= FACE_RECOGNITION_THRESHOLD
```

## Cosine similarity

```text
cos(a, b) = (a · b) / (‖a‖ ‖b‖)
```

Phase 6 stores L2-normalized vectors. For unit vectors, cosine equals the dot product. This project always computes the full cosine formula and verifies equivalence in unit tests.

## Threshold

| Setting | Default |
| --- | --- |
| `FACE_RECOGNITION_ENABLED` | `true` |
| `FACE_RECOGNITION_THRESHOLD` | `0.363` |

**Source of 0.363:** OpenCV DNN Face tutorial / `FaceRecognizerSF` demo for **FR_COSINE** on **LFW**, after the OpenCV `match()` path that L2-normalizes features. Match rule in that documentation: cosine score **≥ 0.363**.

This value is an **initial engineering configuration**. It is **not** validated here as production biometric security (no representative FAR/FRR study in this repo). Other OpenCV datasets list different cosine thresholds (e.g. CALFW 0.340, CPLFW 0.275). Tune for your deployment.

## Unknown / empty / inactive

| Case | Result |
| --- | --- |
| No active enrollment samples | `unknown` / `gallery_empty` |
| Best score &lt; threshold | `unknown` / `below_threshold` (best similarity may be returned for debug) |
| Inactive person | samples ignored (still stored) |
| Quality / alignment / embedding failure | `skipped` with structured reason |

## API

`GET /api/cameras/{id}/detections` tracks may include:

```json
"recognition": {
  "status": "matched",
  "person_id": "...",
  "person_display_name": "Ali",
  "similarity": 0.74,
  "enrollment_id": "..."
}
```

Similarity is a **mathematical score**, not a probability or percentage. Raw embeddings are never returned.

## Webcam

```powershell
.\.venv\Scripts\python.exe scripts/test_webcam.py --show-recognition --log-quality
```

Overlay shows person name + `Similarity: 0.74` (not `%`). Enroll a person first (`docs/PERSON_ENROLLMENT.md`).

## Benchmark

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_face_recognition.py
```

Measures in-memory gallery scan latency at 10 / 100 / 500 samples (not full webcam pipeline).

## Privacy

Local only. No telemetry. Logs may include track_id, person_id, enrollment_id, similarity, status — never raw vectors or frames.

## Security limitations

Face recognition is **not** secure authentication. Risks include printed photos, replay, presentation attacks, lighting/pose variation, look-alikes, and threshold errors. **Liveness detection is not implemented** (future work).

## Known limitations

- Straightforward SQLite/in-memory gallery scan (no FAISS)
- No temporal identity stabilization / events / snapshots
- No production FAR/FRR validation of the threshold
- Linux documented; primary measured environment is Windows 11 CPU

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Always unknown | Enroll samples; person `active=true`; threshold too high |
| Wrong person | Add more enrollments; check lighting/quality gates |
| `gallery_empty` | `alembic upgrade head` + enroll at least one sample |
| Skipped | Quality / alignment / embedding failed upstream |
