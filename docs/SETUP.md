# Setup (Phase 11)

Integrated FastAPI backend + Next.js frontend. Prefer root **`npm run setup`** / **`npm run dev`** / **`npm run test:all`**.

Phase 11 adds production hardening (config fail-fast, readiness, camera recovery, event retention, ops docs). It does **not** change YuNet/SFace thresholds or cooldowns.

**Tested environment:** Windows 11, Python 3.13, Node.js v24+, Intel i7-13700H, CPU only.  
**Documented:** Ubuntu LTS (same Python/venv and Node workflows; Linux webcam latency **NOT HARDWARE-TESTED** in Phase 11).  
**Hardware acceptance:** `docs/ACCEPTANCE_TEST.md` (separate from Playwright).

Operational docs: `docs/OPERATIONS.md`, `docs/SECURITY.md`, `docs/TESTING.md`, `docs/TROUBLESHOOTING.md`.

Automated backend tests **do not** need a physical webcam. Frontend unit tests mock the API. Playwright smoke tests stub `/backend` responses and do not require a webcam.

## One-command workflow (recommended)

### Windows PowerShell

```powershell
npm run setup
python scripts/download_models.py
npm run db:migrate
npm run dev
```

### Linux bash

```bash
npm run setup
python3 scripts/download_models.py
npm run db:migrate
npm run dev
```

`npm run dev` starts:

- Backend: http://127.0.0.1:8000
- Frontend: http://127.0.0.1:3000

Ctrl+C stops both (via `concurrently`).

Full automated checks:

```powershell
npm run test:all
```

Hardware acceptance (real webcam): `docs/ACCEPTANCE_TEST.md`.

### Recognition tests without a webcam (TEST ONLY)

See `docs/RECOGNITION_TESTING.md`. Default `RECOGNITION_TEST_MODE=false` — do **not** enable for normal `npm run dev`.

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_recognition_testing.py -q
```

```bash
cd backend
.venv/bin/python -m pytest tests/test_recognition_testing.py -q
```

| Suite | Doc |
| --- | --- |
| Automated Recognition Tests | `docs/RECOGNITION_TESTING.md` |
| Hardware Recognition Test | `docs/ACCEPTANCE_TEST.md` |
| Browser E2E | `docs/FRONTEND.md` |
| Liveness / Anti-Spoofing | **NOT TESTED** |

### Windows 11

- Python **3.13**
- Node.js **24+** (`node -v`)
- Git (optional)
- USB webcam for live camera UI (optional for automated tests)

```powershell
python --version
node -v
npm -v
```

### Linux / Ubuntu LTS

- Python **3.13**
- Node.js **24+**
- Build tools only if a wheel fails to install (rare for these pins)

```bash
python3.13 --version
node -v
npm -v
```

## Backend virtual environment

### Windows PowerShell

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

### Linux bash

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## Install backend dependencies

`pyproject.toml` is the source of truth:

```powershell
pip install -e ".[dev]"
```

## Environment configuration

Copy the example file from the **project root**:

```powershell
# Windows
cd ..
copy .env.example .env
```

```bash
# Linux
cd ..
cp .env.example .env
```

Settings are loaded from, in order of precedence:

1. Process environment variables
2. `.env` in the project root
3. `backend/.env`

Important variables:

| Variable | Default | Notes |
| --- | --- | --- |
| `HOST` / `PORT` | `127.0.0.1` / `8000` | Backend bind |
| `CORS_ORIGINS` | localhost:3000 | Used if frontend calls `:8000` directly |
| `CAMERA_*` | USB defaults | Device index / backend |
| `FACE_RECOGNITION_*` | see `.env.example` | Do not change casually |

Frontend env (separate file):

```powershell
cd frontend
copy .env.example .env.local
```

```bash
cd frontend
cp .env.example .env.local
```

| Variable | Default | Notes |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | `/backend` | Same-origin proxy path |
| `API_PROXY_TARGET` | `http://127.0.0.1:8000` | Next rewrite target (server-only) |

## Models

From the **project root** (once; needs internet):

```powershell
python scripts/download_models.py
```

See `docs/MODELS.md`.

## Database

From `backend/` with venv active:

```powershell
alembic upgrade head
```

Creates `data/app.db` at the project root (configurable via `DATABASE_URL`).

## Running the backend

```powershell
python -m app
```

Or:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful URLs:

- http://127.0.0.1:8000/api/health
- http://127.0.0.1:8000/api/system/status
- http://127.0.0.1:8000/api/cameras
- http://127.0.0.1:8000/api/cameras/default/preview (MJPEG; camera must be running)
- http://127.0.0.1:8000/docs

## Running the frontend

With the backend already listening on `:8000`:

```powershell
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:3000

Production build:

```powershell
npm run build
npm run start
```

## Development workflow

1. Start backend (`python -m app`)
2. Start frontend (`npm run dev`)
3. Open dashboard → verify health / system status
4. Camera page → Start → confirm MJPEG
5. People → create person
6. Events → confirm list/pagination API
7. Enrollment: person detail → **Enroll Face** (camera session). Dev JSON paste is optional under developer tools.
8. Validate recognition + events (`docs/E2E_FACE_RECOGNITION.md`)

## Backend verification

```powershell
pytest
ruff check .
ruff format --check .
mypy .
```

## Frontend verification

```powershell
npm run lint
npm run typecheck
npm run test
npm run build
```

Optional E2E (install Chromium once; requires network access to Playwright CDN):

```powershell
npm run test:e2e:install
npm run test:e2e
```

If Chromium download fails (timeouts/firewall), E2E is **documented but not runnable** until `npx playwright install chromium` succeeds. Unit/component tests do not need Playwright browsers.

## USB webcam smoke test (backend script)

From `backend/` (physical webcam; not part of pytest):

```powershell
.\.venv\Scripts\python.exe scripts/test_webcam.py --show-recognition --log-events --log-quality
```

### Windows camera problems

- Close apps that hold the webcam exclusively.
- Try another `CAMERA_DEVICE_INDEX` if index `0` is a virtual device.
- Try `CAMERA_BACKEND=msmf` if `dshow` fails.
- Privacy: Windows Settings → Privacy & security → Camera → allow desktop apps.

### Linux camera notes

- Ensure the user can read `/dev/video*`.
- Prefer `CAMERA_BACKEND=any` if the default fails.
- Linux webcam + frontend MJPEG was **documented**, not hardware-revalidated in Phase 9 on Ubuntu.

## How availability is determined

`GET /api/system/status` `camera.available` means a camera is **registered** and not in an error state. A real open happens on `POST /api/cameras/{id}/start` or `scripts/test_webcam.py`.

## Offline use

After Python install, model download, and `npm install`, runtime AI does not call the network. Keep Node registries available only for installing packages.

## Common errors

| Symptom | Likely cause |
| --- | --- |
| Frontend network_error | Backend not running or wrong `API_PROXY_TARGET` |
| Preview blank / stopped | Camera not started |
| Preview stream failed | Backend down mid-stream; use Retry or restart camera |
| Camera failure badge | Capture entered ERROR; Start recovers when `CAMERA_RECOVER_ON_START=true` |
| `/api/ready` 503 | Database down or required models not loaded |
| Settings validation error | Invalid env (not clamped); see `.env.example` |
| `409 camera_invalid_state` on preview | Start the camera first |
| CORS errors | Prefer `/backend` proxy, or add origin to `CORS_ORIGINS` |
| Enrollment 422 | Embedding must be exactly 128 floats; quality.accepted must be true |

See also `docs/TROUBLESHOOTING.md`.
