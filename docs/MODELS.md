# AI Models (Phase 3)

License-first model policy: source-code licenses and pretrained-weight licenses are treated as separate. Do not add a model whose commercial-use status is unclear.

Phase 3 ships **face detection only**. SFace / embeddings / recognition are Phase 4+.

The application **never downloads models at runtime**. After the file is installed, inference is offline (no cloud AI, no telemetry).

## Selected — YuNet face detection

| Field | Value |
| --- | --- |
| Model | YuNet |
| Version | `2023mar` (`face_detection_yunet_2023mar.onnx`) |
| Source | [OpenCV Zoo — face_detection_yunet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) |
| License | **MIT** ([directory LICENSE](https://github.com/opencv/opencv_zoo/blob/main/models/face_detection_yunet/LICENSE); copyright Shiqi Yu) |
| Commercial-use status | Allowed (MIT) |
| Download source | Official Hugging Face mirror: [opencv/face_detection_yunet](https://huggingface.co/opencv/face_detection_yunet) (same SHA-256 as the Zoo LFS object). GitHub `raw` URLs may be Git LFS pointers — do not use those. |
| Size | 232,589 bytes (~227 KB) |
| SHA-256 | `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` |
| Purpose | Face detection + 5 landmarks (right eye, left eye, nose, right mouth corner, left mouth corner) |
| Local path | `models/face/yunet/2023mar.onnx` (gitignored) |

Checksum file committed next to the download location: `models/face/yunet/SHA256SUMS`.

### Runtime

| Item | Value |
| --- | --- |
| Inference | ONNX Runtime, **CPUExecutionProvider only** |
| OpenCV role | Camera capture, resize, pad, preview drawing — **not** `cv2.FaceDetectorYN` / OpenCV DNN for this model |
| Default input size | **640×640** |
| Default detection confidence threshold | `0.7` (starting point, not universally optimal) |
| Default NMS IoU threshold | `0.3` (OpenCV FaceDetectorYN default) |
| Default max faces | `10` |
| Default inference interval | `100` ms |

`confidence` is the YuNet detection score (geometric mean of the classification and objectness heads, matching OpenCV FaceDetectorYN). It is **not** a calibrated probability. Do not report it as “95% probability this is a face”.

### Why 640×640 instead of 320×320

The Phase 3 example listed 320×320 *if compatible*. `face_detection_yunet_2023mar.onnx` is a **fixed-shape** graph (`1×3×640×640`). OpenCV’s DNN backend can reshape it; ONNX Runtime cannot. This project uses ONNX Runtime exclusively, so the configured input size must match the graph.

A 320×320 setting with this file fails at load with a clear error. The later Zoo export `2026may` is dynamic-shape and is **not** used in Phase 3.

### Coordinate system

Detections are mapped back to the **original camera frame**:

- origin: top-left
- units: pixels
- `x` right, `y` down
- box: `x, y, width, height`

The model sees a resized (and stride-32 padded) copy. Padding is bottom/right only so (0, 0) is unchanged. API responses never use the resized-buffer coordinates.

### Install

From the **project root** (internet needed once):

```powershell
python scripts/download_models.py
```

Place the file yourself if you prefer:

```text
models/face/yunet/2023mar.onnx
```

Verify:

```powershell
Get-FileHash models\face\yunet\2023mar.onnx -Algorithm SHA256
```

Expected: `8F2383E4DD3CFBB4553EA8718107FC0423210DC964F9F4280604804ED2552FA4`.

If the file is missing, startup fails with:

```text
YuNet model not found:
<absolute-path>\models\face\yunet\2023mar.onnx
```

### Benchmark

From `backend/` with the virtualenv:

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_face_detection.py
```

This measures inference time and approximate detection FPS on a blank frame. It is a CPU baseline, not a quality target. Recorded numbers belong in the Phase 3 report after a local run.

## Rejected — InsightFace pretrained packs

| Field | Value |
| --- | --- |
| Model | `buffalo_*`, `antelopev2`, and other InsightFace pretrained packs |
| Source | [deepinsight/insightface](https://github.com/deepinsight/insightface) |
| Code license | MIT |
| Pretrained-weight license | Non-commercial research only (maintainer statement, issue [#2486](https://github.com/deepinsight/insightface/issues/2486)) |
| Commercial-use status | **Not suitable for commercial use** |

InsightFace source being MIT does **not** make the weights MIT. Do not add the `insightface` package (it auto-downloads those weights).

## Not in this phase

| Model | When |
| --- | --- |
| SFace `2021dec.onnx` (Apache-2.0, OpenCV Zoo) | Phase 4 embeddings |
| YuNet `2026may` dynamic export | Not needed while 2023mar is the selected detector |
| YuNet INT8 / block-quantized | Only after measurement |
| Any GPU / CUDA EP | Out of scope |
