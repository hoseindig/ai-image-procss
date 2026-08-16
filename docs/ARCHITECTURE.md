# Architecture (Phase 2)

Phase 2 adds a camera abstraction and USB webcam capture. Face detection and recognition are still absent.

## Runtime (current)

```text
HTTP client
    → FastAPI (uvicorn)
        → thin API routes
        → CameraService / SystemStatusService
        → CameraManager (by camera_id)
        → CameraSource (Protocol)
              ├── UsbCameraSource   (OpenCV VideoCapture, production)
              └── FakeCameraSource  (tests only)
        → SQLite (unchanged from Phase 1)
```

OpenCV is imported only inside `app.cameras.usb`. Routes, services, and `CameraManager` never see `cv2.VideoCapture`.

## Camera lifecycle

```text
closed → open() → open → start() → running → stop() → stopped → close() → closed
```

Invalid transitions raise domain errors (`CameraInvalidStateError`, `CameraAlreadyRunningError`, …). `close()` is idempotent and always releases the device.

The HTTP API maps:

- `POST /start` → open (if needed) + start
- `POST /stop` → stop + close (releases the Windows webcam handle)

## Capture design

`UsbCameraSource` uses a **single dedicated capture thread** and a **size-1 latest-frame slot** (`LatestFrameSlot`).

- The thread is not a daemon; `stop()`/`close()` set an event and `join()` with a timeout.
- A new frame **replaces** the previous one. There is no growing queue.
- Stale frames are dropped on purpose so RAM cannot grow if a consumer is slow.
- Successful frames are not logged.

Requested width/height/FPS are sent to the driver. If the webcam ignores them, capture continues with the **actual** values reported by OpenCV.

On Windows the opener tries **DirectShow (`dshow`)** first, then **Media Foundation (`msmf`)**, then OpenCV’s default. Device indexes are not scanned.

## Layout

```text
backend/
  app/
    cameras/             # Protocol, USB source, manager, domain errors
    api/routes/cameras.py
    services/camera.py
  scripts/test_webcam.py # manual hardware smoke test
  tests/fake_camera.py   # in-process CameraSource for automated tests
```

## Configuration

Camera defaults live on the same `Settings` object as Phase 1 (`CAMERA_*` environment variables). There is no second config system and no camera table in SQLite.

## API

| Method | Path | Role |
| --- | --- | --- |
| GET | `/api/health` | Liveness (unchanged) |
| GET | `/api/system/status` | Adds `camera.available` / `camera.running` (no hardware probe) |
| GET | `/api/cameras` | Registered cameras and status |
| GET | `/api/cameras/{id}` | One camera |
| POST | `/api/cameras/{id}/start` | Open + capture |
| POST | `/api/cameras/{id}/stop` | Stop + release |

`available` means a camera is registered and not in `error`. It does **not** mean a USB probe succeeded.

## Future sources (not implemented)

`SourceType` already includes `rtsp`, `file`, and `http`. `default_source_factory` only constructs `UsbCameraSource`. New implementations can follow the same `CameraSource` protocol without changing the manager or API shape.

See `docs/IMPLEMENTATION_PLAN.md` for later phases.
