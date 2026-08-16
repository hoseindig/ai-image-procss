# Local-First Face Recognition Camera

Local, CPU-only face detection and recognition for a USB webcam. No cloud AI APIs and no paid services.

**Phases 0–10 are implemented** (backend through camera enrollment + Next.js UI). Plate recognition / OCR are not in this phase.

See `docs/IMPLEMENTATION_PLAN.md` for the full roadmap.

## Requirements

- Windows 11 (primary target) or Ubuntu LTS (documented)
- Python 3.13
- Node.js **24+** (frontend)
- One USB webcam (live capture / smoke test)
- YuNet + SFace ONNX files (see `docs/MODELS.md`; download once, then offline)
- Intel Core i7-class CPU, 16 GB RAM, no GPU required

## Quick start (Windows PowerShell)

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
cd ..
copy .env.example .env
python scripts/download_models.py
cd backend
alembic upgrade head
python -m app
```

Health: http://127.0.0.1:8000/api/health

### Frontend

```powershell
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

UI: http://127.0.0.1:3000

The frontend proxies `/backend/*` to `http://127.0.0.1:8000` (see `docs/FRONTEND.md`).

### Root convenience scripts

From the project root (Node only; does not replace the Python venv):

```powershell
npm run frontend:install
npm run frontend:dev
npm run frontend:build
npm run frontend:test
```

## Quick start (Linux / Ubuntu LTS bash)

### Backend

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
cd ..
cp .env.example .env
python scripts/download_models.py
cd backend
alembic upgrade head
python -m app
```

### Frontend

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

## Tests

### Backend (from `backend/` with venv active)

```powershell
pytest
ruff check .
ruff format --check .
mypy .
```

### Frontend (from `frontend/`)

```powershell
npm run lint
npm run typecheck
npm run test
npm run build
```

Optional Playwright smoke (mocked backend; no webcam):

```powershell
npm run test:e2e:install
npm run test:e2e
```

## Key endpoints

| Path | Role |
| --- | --- |
| `GET /api/health` | process health |
| `GET /api/system/status` | DB / camera / AI flags |
| `GET/POST /api/cameras…` | list, start, stop, detections |
| `GET /api/cameras/{id}/preview` | MJPEG live preview |
| `GET/POST /api/persons…` | gallery + **enrollment-sessions** |
| `GET /api/events` | paginated audit events |

## Documentation

- [Setup](docs/SETUP.md) — Windows + Linux
- [Frontend](docs/FRONTEND.md) — Next.js architecture, proxy, RTL
- [Face enrollment](docs/FACE_ENROLLMENT.md) — camera enrollment sessions
- [E2E face recognition](docs/E2E_FACE_RECOGNITION.md) — known/unknown/cooldown checklist
- [Architecture](docs/ARCHITECTURE.md)
- [Dependencies](docs/DEPENDENCIES.md)
- [Models](docs/MODELS.md)
- [Tracking](docs/TRACKING.md)
- [Face quality & alignment](docs/FACE_QUALITY.md)
- [Face embedding](docs/FACE_EMBEDDING.md)
- [Person enrollment](docs/PERSON_ENROLLMENT.md)
- [Face recognition](docs/FACE_RECOGNITION.md)
- [Events](docs/EVENTS.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)

## Phase status

| Topic | Status |
| --- | --- |
| Face pipeline through events | Done (Phases 0–8) |
| Frontend foundation | Done (Phase 9) |
| Camera enrollment + E2E validation | Done (Phase 10) |
| Plate / OCR / vehicles | Future only |
| WebSockets | Future |

## Troubleshooting

Camera access: `docs/SETUP.md`. Frontend proxy / RTL: `docs/FRONTEND.md`.
