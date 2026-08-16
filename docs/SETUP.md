# Setup (Phase 7A)

Phase 7A runs the FastAPI backend with USB webcam capture, YuNet detection, IoU tracking, face quality/alignment, SFace embedding, and **SQLite person enrollment / face gallery**. It does not require Node.js, Redis, PostgreSQL, Docker, or internet after Python packages and the model files are installed.

Automated tests **do not** need a physical webcam. A fake camera and a fake detector are used instead. Tests that need the real ONNX file are skipped if it is not present.

**Tested environment:** Windows 11, Python 3.13, Intel i7-13700H, CPU only.  
**Also documented:** Ubuntu LTS (Linux) with the same Python/venv workflow — Linux hardware latency has not been measured in this repository.

Automated tests **do not** need a physical webcam. Tests that need ONNX files skip if the models are absent.



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
| `FACE_TRACKING_ENABLED` | `true` | Associate detections across frames |
| `FACE_TRACKING_IOU_THRESHOLD` | `0.3` | Minimum IoU for an IoU match |
| `FACE_TRACKING_MAX_CENTROID_DISTANCE` | `100` | Pixel fallback when IoU is low |
| `FACE_TRACKING_MAX_MISSED_FRAMES` | `5` | Consecutive misses a track can survive |
| `FACE_TRACKING_MIN_CONFIRMED_FRAMES` | `2` | Hits before a track is `confirmed` |
| `FACE_TRACKING_MAX_TRACKS` | `20` | Cap on simultaneous tracks |
| `FACE_QUALITY_ENABLED` | `true` | Assess tracked faces for alignment suitability |
| `FACE_QUALITY_MIN_FACE_WIDTH` | `80` | Reject smaller face boxes |
| `FACE_QUALITY_MIN_FACE_HEIGHT` | `80` | Reject smaller face boxes |
| `FACE_QUALITY_MIN_SHARPNESS` | `60` | Laplacian variance heuristic (not a blur probability) |
| `FACE_QUALITY_MIN_BRIGHTNESS` | `40` | Mean gray lower bound (0–255) |
| `FACE_QUALITY_MAX_BRIGHTNESS` | `220` | Mean gray upper bound (0–255) |
| `FACE_ALIGNMENT_ENABLED` | `true` | Produce aligned crops for accepted faces |
| `FACE_ALIGNMENT_WIDTH` | `112` | Aligned output width (SFace input) |
| `FACE_ALIGNMENT_HEIGHT` | `112` | Aligned output height |
| `FACE_EMBEDDING_ENABLED` | `true` | Load SFace and embed accepted aligned faces |
| `FACE_EMBEDDING_MODEL_PATH` | `models/face/sface/2021dec.onnx` | Relative paths resolve from the **project root** |
| `FACE_EMBEDDING_THREADS` | `2` | ONNX Runtime intra-op threads for SFace |

Do not commit `.env`.

## YuNet + SFace models

The application will **not** download models. From the project root:

**Windows**

```powershell
python scripts/download_models.py
```

**Linux (Ubuntu LTS)**

```bash
python3 scripts/download_models.py
```

Expected paths:

- `models/face/yunet/2023mar.onnx`
- `models/face/sface/2021dec.onnx`

Checksums: `docs/MODELS.md`.

## Database migrations

From `backend/` with the virtualenv active:

```powershell
alembic upgrade head
```

Revision `0002_person_enrollment` creates `persons` and `enrollment_samples`. See `docs/PERSON_ENROLLMENT.md`.

Useful commands:

```powershell
alembic current
alembic downgrade 0001_initial
alembic upgrade head
alembic history
```

The SQLite parent directory (`data/`) is created automatically if it is missing.

### SQLite backup

Stop the app before a simple file copy, or use:

```powershell
sqlite3 data\app.db ".backup 'data\app-backup.db'"
```

Details: `docs/PERSON_ENROLLMENT.md`.

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

The window shows the live feed with **Track #N**, quality OK/REJECTED when enabled, and five landmarks. Press **Q** to exit. The script always releases the camera.

Camera-only (no YuNet):

```powershell
.\.venv\Scripts\python.exe scripts/test_webcam.py --no-detect
```

CPU baseline (blank/synthetic frames, no webcam):

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_face_detection.py
.\.venv\Scripts\python.exe scripts/benchmark_face_tracking.py
.\.venv\Scripts\python.exe scripts/benchmark_face_quality.py
.\.venv\Scripts\python.exe scripts/benchmark_face_embedding.py
```

SFace overlay (metadata only, no raw vector):

```powershell
.\.venv\Scripts\python.exe scripts/test_webcam.py --show-embedding
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

## Development flow (Phase 7A)

1. Create/activate `backend/.venv` (Windows PowerShell or Linux bash)
2. `pip install -e ".[dev]"`
3. Copy `.env.example` to `.env`
4. From the project root: `python scripts/download_models.py`
5. `alembic upgrade head` (creates `persons` / `enrollment_samples`)
6. `pytest`, `ruff check .`, `ruff format --check .`, `mypy .`
7. `python -m app`
8. Optional: create a person via `POST /api/persons` (see `docs/PERSON_ENROLLMENT.md`)
9. Optional: `scripts/test_webcam.py --show-embedding`
10. Optional: `scripts/benchmark_face_embedding.py`

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
