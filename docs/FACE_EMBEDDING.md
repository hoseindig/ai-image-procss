# Face embedding (Phase 6)

Phase 6 generates **128-dimensional** face embeddings from quality-accepted, aligned crops using OpenCV Zoo **SFace**. It does **not** recognize people, store identities, or match embeddings.

**Track ID ≠ Person ID.** Embeddings are biometric-sensitive; this phase keeps them in the vision pipeline only (size-1 slot). They are not uploaded and are not returned by the default REST API.

## Pipeline

```text
FaceTrack → FaceQualityAssessor → (accepted) → FaceAligner → AlignedFace
    → FaceEmbedder (SFaceEmbedder) → FaceEmbedding
```

Rejected quality faces and missing alignments skip SFace (`embedding.status=skipped`).

## Model

| Field | Value |
| --- | --- |
| Name | SFace |
| Version | `2021dec` (`face_recognition_sface_2021dec.onnx`) |
| Source | [OpenCV Zoo — face_recognition_sface](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface) |
| Download | [Hugging Face opencv/face_recognition_sface](https://huggingface.co/opencv/face_recognition_sface) |
| License | **Apache-2.0** |
| SHA-256 | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` |
| Size | 38,696,353 bytes |
| Local path | `models/face/sface/2021dec.onnx` |
| Input (verified) | `data` — `1×3×112×112` float32 |
| Output (verified) | `fc1` — `1×128` float32 |
| Provider | `CPUExecutionProvider` only |

Install (project root, once):

```powershell
python scripts/download_models.py
```

Linux:

```bash
python scripts/download_models.py
```

The app never downloads models at runtime.

## Preprocessing (verified)

Matches OpenCV `FaceRecognizerSF::feature` (`modules/objdetect/src/face_recognize.cpp`):

```text
dnn::blobFromImage(aligned, scalefactor=1.0, size=112x112,
                   mean=(0,0,0), swapRB=true, crop=false)
```

| Step | Value |
| --- | --- |
| Source | Phase 5 `AlignedFace` BGR `112×112` uint8 |
| Color | BGR → RGB (`swapRB=true`) |
| Scaling | `1.0` (pixel values stay ~0–255 as float32) |
| Mean / std | none |
| Layout | NCHW `1×3×112×112` |
| dtype | float32 |

## Normalization

OpenCV `FaceRecognizerSF::match` L2-normalizes both vectors before cosine / L2 distance. This phase applies the same **L2 normalization** after inference so vectors are comparison-ready for a future matcher. Cosine threshold `0.363` is **not** used here (no recognition).

## Configuration

| Variable | Default |
| --- | --- |
| `FACE_EMBEDDING_ENABLED` | `true` |
| `FACE_EMBEDDING_MODEL_PATH` | `models/face/sface/2021dec.onnx` |
| `FACE_EMBEDDING_THREADS` | `2` (ONNX Runtime intra-op threads) |

## API

`GET /api/cameras/{id}/detections` may include per-track:

```json
"embedding": { "status": "generated", "dimension": 128, "normalized": true }
```

or `skipped` / `failed` with a structured `reason`. **Raw 128-D vectors are never returned** on this endpoint.

## Webcam debug

```powershell
.\.venv\Scripts\python.exe scripts/test_webcam.py --show-embedding
```

Overlay shows `Embedding: 128-D` (metadata only).

## Privacy

Face embeddings are biometric identifiers. Do not log raw vectors, upload them, or treat Track IDs as person identity.

## Known limitations

- No identity matching in Phase 6; gallery persistence is Phase 7A (`docs/PERSON_ENROLLMENT.md`).
- Embedding quality depends on Phase 5 gates (size, blur, lighting, landmarks).
- Extreme pose / occlusion can produce embeddings that would fail future matching.
- Linux is documented; primary measured environment in this repo is Windows 11 CPU.
