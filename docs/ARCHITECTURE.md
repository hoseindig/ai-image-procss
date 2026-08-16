# Architecture (Phase 3)

Phase 3 adds CPU face detection on top of the Phase 2 camera pipeline. Face recognition, tracking, events, and the frontend are still absent.

## Runtime (current)

```text
USB Webcam
    → CameraSource (UsbCameraSource)
    → CameraManager (latest-frame slot)
    → DetectionWorker (interval, latest-result slot)
    → FaceDetector
          └── YuNetFaceDetector
                └── InferenceEngine (OnnxRuntimeEngine, CPUExecutionProvider)
    → FaceDetection (box + 5 landmarks + confidence)
    → visualization (preview only; not part of the detector)
    → REST (camera status + latest detections)
```

```text
HTTP client
    → FastAPI
        → thin API routes
        → CameraService / DetectionService / SystemStatusService
        → CameraManager + DetectionRuntime
        → FaceDetector (protocol)
        → SQLite (unchanged)
```

OpenCV is used for capture, resize/pad, and drawing. ONNX Runtime is the only inference backend. Routes never import `onnxruntime` or YuNet session objects.

## FaceDetector

Application code depends on `FaceDetector`, not `YuNetFaceDetector`.

```text
FaceDetector.detect(frame) → list[FaceDetection]
```

`FaceDetection` contains:

- `bounding_box` (`x`, `y`, `width`, `height`) in the **original frame**
- `confidence` (YuNet detection score, not a probability)
- `landmarks` (`left_eye`, `right_eye`, `nose`, `left_mouth`, `right_mouth`)

`InferenceEngine` hides the ONNX session. `OnnxRuntimeEngine` requests `CPUExecutionProvider` explicitly and refuses to start if that provider is not active.

## Latest-frame scheduling

There is still **no frame queue**.

```text
Camera thread  → LatestFrameSlot (size 1)
Detection thread → polls newest frame on inference_interval_ms
                 → LatestValueSlot[DetectionSnapshot] (size 1)
```

If inference is slower than the camera, older frames are skipped. The worker is not a daemon; shutdown stops the detection worker first, then the camera.

## Coordinate mapping

```text
original BGR frame
    → resize to configured input size
    → pad bottom/right to a multiple of 32
    → NCHW float32 blob (no mean/std normalization)
    → YuNet
    → decode + NMS in padded space
    → scale back to original width/height
```

API coordinates always refer to the original frame, origin top-left.

## Layout

```text
backend/
  app/
    cameras/             # Phase 2
    vision/              # FaceDetector, YuNet, ONNX engine, worker
    api/routes/cameras.py
    services/camera.py
    services/detection.py
  scripts/test_webcam.py
  scripts/benchmark_face_detection.py
models/face/yunet/       # gitignored ONNX; SHA256SUMS is committed
scripts/download_models.py
```

## Configuration

Face-detection settings live on the same `Settings` object (`FACE_DETECTION_*`). There is no second config system and no model download in the app process.

## API

| Method | Path | Role |
| --- | --- | --- |
| GET | `/api/health` | Liveness |
| GET | `/api/system/status` | Adds `face_detection` (enabled / model_loaded / provider / last_inference_ms) |
| GET | `/api/cameras` | Registered cameras |
| GET | `/api/cameras/{id}` | One camera |
| POST | `/api/cameras/{id}/start` | Open + capture + attach detection worker |
| POST | `/api/cameras/{id}/stop` | Detach worker + stop + release |
| GET | `/api/cameras/{id}/detections` | Latest boxes/landmarks (no image bytes) |

Missing YuNet file: process startup fails with `YuNet model not found:` and the absolute path.

See `docs/MODELS.md` for license, SHA-256, and why the default input is 640×640.
