# AI Models

License-first model policy: source-code licenses and pretrained-weight licenses are treated as separate. Do not add a model whose commercial-use status is unclear.

Phases 3–6 ship **YuNet detection** and **SFace embedding**. Recognition / person identity are later phases.

The application **never downloads models at runtime**. After files are installed, inference is offline (no cloud AI, no telemetry).

## Selected — YuNet face detection

| Field | Value |
| --- | --- |
| Model | YuNet |
| Version | `2023mar` (`face_detection_yunet_2023mar.onnx`) |
| Source | [OpenCV Zoo — face_detection_yunet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) |
| License | **MIT** |
| Download | [opencv/face_detection_yunet](https://huggingface.co/opencv/face_detection_yunet) |
| Size | 232,589 bytes |
| SHA-256 | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |
| Local path | `models/face/yunet/2023mar.onnx` |
| Runtime | ONNX Runtime `CPUExecutionProvider` only |
| Input | fixed `1×3×640×640` |

## Selected — SFace face embedding

| Field | Value |
| --- | --- |
| Model | SFace |
| Version | `2021dec` (`face_recognition_sface_2021dec.onnx`) |
| Source | [OpenCV Zoo — face_recognition_sface](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface) |
| License | **Apache-2.0** |
| Download | [opencv/face_recognition_sface](https://huggingface.co/opencv/face_recognition_sface) |
| Size | 38,696,353 bytes |
| SHA-256 | `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` |
| Local path | `models/face/sface/2021dec.onnx` |
| Runtime | ONNX Runtime `CPUExecutionProvider` only |
| Input (verified) | `data` `1×3×112×112` float32 |
| Output (verified) | `fc1` `1×128` float32 |

See `docs/FACE_EMBEDDING.md` for preprocessing and L2 normalization details.

## Install

From the **project root** (internet needed once):

```powershell
python scripts/download_models.py
```

```bash
python scripts/download_models.py
```

Verify:

```powershell
Get-FileHash models\face\yunet\2023mar.onnx -Algorithm SHA256
Get-FileHash models\face\sface\2021dec.onnx -Algorithm SHA256
```

## Rejected — InsightFace pretrained packs

| Field | Value |
| --- | --- |
| Models | `buffalo_*`, `antelopev2`, etc. |
| Pretrained-weight license | Non-commercial research only |
| Status | **Not suitable for commercial use** |

Do not add the `insightface` package.

## Not in this phase

| Topic | When |
| --- | --- |
| Person enrollment / gallery | Phase 7A |
| Recognition / matching | Phase 7B+ |
| GPU / CUDA EP | Out of scope for v1 |
| SFace INT8 | Only after measurement |
