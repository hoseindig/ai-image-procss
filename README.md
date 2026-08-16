# Local-First Face Recognition Camera

Local, CPU-only face detection and recognition for a USB webcam. No cloud AI APIs and no paid services.

This repository is being built in gated phases. **Phases 0–4 are implemented** (backend, USB camera, YuNet detection, IoU face tracking). Recognition and the frontend are not in this phase.

See `docs/IMPLEMENTATION_PLAN.md` for the full roadmap.

## Requirements

- Windows 11 (primary target)
- Python 3.13
- Node.js 24+ (needed from Phase 5/9; not required for Phase 3)
- One USB webcam (live capture / smoke test)
- YuNet ONNX file (see `docs/MODELS.md`; download once, then offline)
- Intel Core i7-class CPU, 16 GB RAM, no GPU required

## Phase 1 — Backend foundation

The backend is a FastAPI application with SQLite, Alembic, structured logging, and health endpoints.

### Python setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### Environment configuration

```powershell
cd ..
copy .env.example .env
```

Edit `.env` if you need non-default host, port, camera index, or detection settings. Do not commit `.env`.

### YuNet model

From the **project root** (once; requires internet):

```powershell
python scripts/download_models.py
```

The app does not download models at startup. See `docs/MODELS.md`.

### Database setup

From `backend/`:

```powershell
alembic upgrade head
```

This creates `data/app.db` at the project root (path is configurable via `DATABASE_URL`).

### Running the backend

From `backend/` with the virtualenv active:

```powershell
python -m app
```

Or:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open:

- http://127.0.0.1:8000/api/health
- http://127.0.0.1:8000/api/system/status
- http://127.0.0.1:8000/api/cameras
- http://127.0.0.1:8000/api/cameras/default/detections
- http://127.0.0.1:8000/docs

### USB webcam smoke test

From `backend/` (requires a physical webcam and the YuNet file; not part of pytest):

```powershell
.\.venv\Scripts\python.exe scripts/test_webcam.py
```

Press Q to quit. Boxes show **Track #N** plus detection confidence. Use `--no-detect` for camera-only. See `docs/SETUP.md` for device index, Windows privacy, and “camera in use” issues.

CPU baseline (no webcam):

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_face_detection.py
.\.venv\Scripts\python.exe scripts/benchmark_face_tracking.py
```

### Tests, lint, type checks

From `backend/`:

```powershell
pytest
ruff check .
ruff format --check .
mypy .
```

Format in place (optional):

```powershell
ruff format .
```

## Later phases (not implemented yet)

| Topic | Status |
| --- | --- |
| Selecting a webcam | Phase 2 (done) |
| Face detection (YuNet) | Phase 3 (done) |
| Face tracking (IoU) | Phase 4 (done) |
| Registering a person / recognition | Phases 5–6 |
| Frontend | Phase 9 |
| Model download | Phase 3 (done; `scripts/download_models.py`) |
| E2E tests | Phase 10 |

## Documentation

- [Setup](docs/SETUP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Dependencies](docs/DEPENDENCIES.md)
- [Models](docs/MODELS.md)
- [Tracking](docs/TRACKING.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)

## Troubleshooting camera access / CPU tuning

Camera access: `docs/SETUP.md` (Windows Camera privacy, exclusive device, index, `dshow` vs `msmf`). CPU tuning remains Phase 11.
