# Setup (Phase 3)

Phase 3 runs the FastAPI backend with USB webcam capture and **local YuNet face detection**. It does not require Node.js, Redis, PostgreSQL, Docker, or internet after Python packages and the YuNet file are installed.

Automated tests **do not** need a physical webcam. A fake camera and a fake detector are used instead. Tests that need the real ONNX file are skipped if it is not present.

## Prerequisites

- Windows 11
- Python **3.13** (`python --version` should print `3.13.x`)
- Git (optional, for version control)

Confirm Python:

```powershell
python --version
```

## Virtual environment

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Install dependencies

`pyproject.toml` is the source of truth. Install the package in editable mode with development extras (pytest, ruff, mypy):

```powershell
pip install -e ".[dev]"
```

## Environment configuration

Copy the example file from the **project root**:

```powershell
cd ..
copy .env.example .env
```

Settings are loaded from, in order of precedence:

1. Process environment variables
2. `backend/.env` if present
3. Project-root `.env` if present
4. Built-in development defaults

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `Local Face Camera` | OpenAPI title / log identity |
| `APP_ENV` | `development` | Environment name reported by `/api/system/status` |
| `DEBUG` | `true` | Include exception `details` in 500 responses; uvicorn reload when using `python -m app` |
| `HOST` | `127.0.0.1` | Bind address for `python -m app` |
| `PORT` | `8000` | Bind port for `python -m app` |
| `DATABASE_URL` | `sqlite:///./data/app.db` | SQLAlchemy URL. Relative SQLite paths resolve from the **project root**. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated browser origins. `*` is rejected. |
| `CAMERA_DEFAULT_ID` | `default` | ID of the registered USB camera |
| `CAMERA_DEFAULT_NAME` | `USB Webcam` | Display name |
| `CAMERA_DEVICE_INDEX` | `0` | OpenCV device index (try `1` if `0` is the wrong device) |
| `CAMERA_WIDTH` | `1280` | **Requested** frame width; not guaranteed |
| `CAMERA_HEIGHT` | `720` | **Requested** frame height; not guaranteed |
| `CAMERA_FPS` | `15` | **Requested** FPS; not guaranteed |
| `CAMERA_BACKEND` | `dshow` | Windows: `dshow`, `msmf`, or `any` |
| `FACE_DETECTION_ENABLED` | `true` | Load YuNet at startup when true |
| `FACE_DETECTION_MODEL_PATH` | `models/face/yunet/2023mar.onnx` | Relative paths resolve from the **project root** |
| `FACE_DETECTION_CONFIDENCE_THRESHOLD` | `0.7` | YuNet detection-score cutoff (not a probability) |
| `FACE_DETECTION_NMS_THRESHOLD` | `0.3` | IoU NMS; OpenCV FaceDetectorYN default |
| `FACE_DETECTION_INPUT_WIDTH` | `640` | Must match the 2023mar ONNX graph |
| `FACE_DETECTION_INPUT_HEIGHT` | `640` | Must match the 2023mar ONNX graph |
| `FACE_DETECTION_MAX_FACES` | `10` | After NMS |
| `FACE_DETECTION_INFERENCE_INTERVAL_MS` | `100` | Detection worker period; camera FPS can be higher |

Do not commit `.env`.

## YuNet model

The application will **not** download the model. From the project root:

```powershell
python scripts/download_models.py
```

Expected path: `models/face/yunet/2023mar.onnx` (232,589 bytes, SHA-256 listed in `docs/MODELS.md`).

If the file is missing and `FACE_DETECTION_ENABLED=true`, startup fails with:

```text
YuNet model not found:
<project>\models\face\yunet\2023mar.onnx
```

After that install step, detection runs offline.

## Database migrations

From `backend/` with the virtualenv active:

```powershell
alembic upgrade head
```

Phase 1’s initial revision does not create application tables yet; it records Alembic history and creates the SQLite file.

Useful commands:

```powershell
alembic current
alembic downgrade base
alembic upgrade head
alembic history
```

The SQLite parent directory (`data/`) is created automatically if it is missing.

## Start the backend

From `backend/`:

```powershell
python -m app
```

Equivalent:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Check:

```powershell
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/system/status
```

On Windows PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/system/status
```

Interactive docs: http://127.0.0.1:8000/docs

Latest detections for the default camera (empty until start):

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/cameras/default/detections
```

## Tests

From `backend/`:

```powershell
pytest
```

Tests use a temporary SQLite file and a fake camera. They do not need a physical webcam, network, or `data/app.db`. Tests that exercise the real YuNet file skip if `models/face/yunet/2023mar.onnx` is absent.

## USB webcam (manual)

Select the device with `CAMERA_DEVICE_INDEX` (default `0`). This project does **not** scan many indexes.

From `backend/` with the virtualenv active:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/test_webcam.py
```

Without activating the venv:

```powershell
.\.venv\Scripts\python.exe scripts/test_webcam.py
```

Optional flags: `--index 1`, `--width 640`, `--height 480`, `--fps 15`, `--frames 30`, `--no-display`.

The window shows the live feed with face boxes, detection confidence, and five landmarks. Press **Q** to exit. The script always releases the camera.

Camera-only (no YuNet):

```powershell
.\.venv\Scripts\python.exe scripts/test_webcam.py --no-detect
```

CPU baseline (blank frames, no webcam):

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_face_detection.py
```

Requested resolution/FPS are hints. The printed “actual” size is what the driver provided.

### Windows camera problems

- Close the Windows Camera app, Teams, Zoom, or any other program using the webcam. DirectShow usually allows only one opener.
- If index `0` is a virtual camera (IR, OBS), try `--index 1`.
- If `dshow` fails, set `CAMERA_BACKEND=msmf` and retry.
- Privacy: Windows Settings → Privacy & security → Camera → allow desktop apps.
- After a crash, unplug/replug the USB camera if the handle looks stuck.

### How availability is determined

`GET /api/system/status` `camera.available` means a camera is **registered** and not in an error state. It does not open the device. A real open happens only on `POST /api/cameras/{id}/start` or `scripts/test_webcam.py`.

## Development flow (Phase 3)

1. Create/activate `backend/.venv`
2. `pip install -e ".[dev]"`
3. Copy `.env.example` to `.env`
4. From the project root: `python scripts/download_models.py`
5. `alembic upgrade head`
6. `pytest`, `ruff check .`, `ruff format --check .`, `mypy .`
7. `python -m app`
8. Hit `/api/health`, `/api/system/status`, `/api/cameras`
9. Optional: `.\.venv\Scripts\python.exe scripts/test_webcam.py`
10. Optional: `.\.venv\Scripts\python.exe scripts/benchmark_face_detection.py`

## Lint

```powershell
ruff check .
ruff format --check .
```

Apply formatting:

```powershell
ruff format .
```

## Type checking

```powershell
mypy .
```

## Offline use

After `pip install` and `python scripts/download_models.py`, the backend does not call the network. Face detection does not upload frames.
