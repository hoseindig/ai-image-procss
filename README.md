# Local-First Face Recognition Camera

Local, CPU-only face detection and recognition for a USB webcam. No cloud AI APIs and no paid services.

**Phases 0–10.5:** backend pipeline, Next.js UI, camera enrollment, and one-command integrated run. Plate/OCR/vehicles are out of scope.

## Requirements

- Windows 11 (primary) or Ubuntu LTS (documented)
- Python **3.13**
- Node.js **24+**
- One USB webcam (for hardware acceptance)
- YuNet + SFace ONNX files (`docs/MODELS.md`)

## Quick start (Windows PowerShell)

```powershell
# 1) Install Node + Python deps (does NOT download models or migrate DB)
npm run setup

# 2) Models (once; needs network)
python scripts/download_models.py

# 3) Database
npm run db:migrate

# 4) Backend + frontend together
npm run dev
```

Open:

- Frontend: http://127.0.0.1:3000
- Backend health: http://127.0.0.1:8000/api/health

Stop with **Ctrl+C** (stops both processes).

## Quick start (Linux / Ubuntu LTS bash)

```bash
npm run setup
python3 scripts/download_models.py
npm run db:migrate
npm run dev
```

## What `npm run setup` does

- `npm install` at repo root (adds `concurrently` for `npm run dev`)
- `npm install` in `frontend/`
- Creates `backend/.venv` if missing and `pip install -e ".[dev]"`
- Copies `.env.example` → `.env` and `frontend/.env.example` → `frontend/.env.local` **only if missing**

It does **not** download models, run migrations, delete databases, or delete virtualenvs.

## One-command tests

```powershell
npm run test:all
```

Runs backend pytest/ruff/mypy and frontend test/lint/typecheck/build. Playwright E2E runs if Chromium is available; otherwise it reports **BLOCKED** (not PASS).

### Test suite statuses (keep separate)

| Suite | Status / notes |
| --- | --- |
| Automated Recognition Tests | No webcam; see `docs/RECOGNITION_TESTING.md` (`RECOGNITION_TEST_MODE` default **false**) |
| Hardware Recognition Test | USB webcam; `docs/ACCEPTANCE_TEST.md` |
| Browser E2E | Playwright mocked backend; optional Chromium install |
| Liveness / Anti-Spoofing | **NOT TESTED** |

Install Chromium once (optional):

```powershell
npm run frontend:e2e:install
```

## Documentation

- [Setup](docs/SETUP.md)
- [Recognition testing (TEST ONLY, no webcam)](docs/RECOGNITION_TESTING.md)
- [Acceptance test (hardware)](docs/ACCEPTANCE_TEST.md)
- [Frontend](docs/FRONTEND.md)
- [Face enrollment](docs/FACE_ENROLLMENT.md)
- [E2E face recognition notes](docs/E2E_FACE_RECOGNITION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Dependencies](docs/DEPENDENCIES.md)
- [Models](docs/MODELS.md)

## Phase status

| Topic | Status |
| --- | --- |
| Face pipeline + events | Done (0–8) |
| Frontend foundation | Done (9) |
| Camera enrollment | Done (10) |
| One-command run + acceptance docs | Done (10.5) |
| Plate / OCR / vehicles | Future |
