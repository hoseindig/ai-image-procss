# Architecture (Phase 4)

Phase 4 adds lightweight face tracking on top of YuNet detection. Recognition, events, and the frontend are still absent.

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
    → visualization (preview only; not part of detector or tracker)
    → REST (camera status + latest detections/tracks)
```

`FaceDetector` does not know about tracking. `FaceTracker` does not know about YuNet or ONNX Runtime.

## FaceTracker

```text
FaceTracker.update(detections) → list[FaceTrack]
```

`FaceTrack` contains:

- `track_id` (process-local integer; **not** a person ID)
- `bounding_box` / `landmarks` / `confidence` in the original frame
- `age_frames`, `missed_frames`
- `state`: `tentative` | `confirmed` | `lost`

Association is greedy IoU-first with centroid-distance fallback. See `docs/TRACKING.md`.

## Latest-frame scheduling

Unchanged from Phase 3:

```text
Camera thread  → LatestFrameSlot (size 1)
Detection thread → detect → track → LatestValueSlot[DetectionSnapshot] (size 1)
```

No frame queue. Tracking runs on the same worker thread as detection. Shutdown stops the worker (and tracker), then the camera.

## Layout

```text
backend/
  app/
    cameras/
    vision/              # detector, YuNet, tracker, worker
    services/detection.py
  scripts/test_webcam.py
  scripts/benchmark_face_detection.py
  scripts/benchmark_face_tracking.py
```

## API

| Method | Path | Role |
| --- | --- | --- |
| GET | `/api/health` | Liveness |
| GET | `/api/system/status` | Adds `face_detection.tracking_enabled` |
| GET | `/api/cameras` | Registered cameras |
| GET | `/api/cameras/{id}` | One camera |
| POST | `/api/cameras/{id}/start` | Open + capture + attach detection/tracking worker |
| POST | `/api/cameras/{id}/stop` | Detach worker + stop + release |
| GET | `/api/cameras/{id}/detections` | Latest `faces` (raw detections) and `tracks` |

Raw `faces` remain Phase 3 detections. `tracks` add `track_id` and `state`.
