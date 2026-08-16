# Setup (Phase 2)

Phase 2 runs the FastAPI backend with USB webcam capture. It does not require AI models, Node.js, or internet after Python packages are installed.

Automated tests **do not** need a physical webcam. A fake camera implementation is used instead.

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

Do not commit `.env`.

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

## Tests

From `backend/`:

```powershell
pytest
```

Tests use a temporary SQLite file and a fake camera. They do not need a physical webcam, network, or `data/app.db`.

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

The window shows the live feed. Press **Q** to exit. The script always releases the camera.

Requested resolution/FPS are hints. The printed “actual” size is what the driver provided.

### Windows camera problems

- Close the Windows Camera app, Teams, Zoom, or any other program using the webcam. DirectShow usually allows only one opener.
- If index `0` is a virtual camera (IR, OBS), try `--index 1`.
- If `dshow` fails, set `CAMERA_BACKEND=msmf` and retry.
- Privacy: Windows Settings → Privacy & security → Camera → allow desktop apps.
- After a crash, unplug/replug the USB camera if the handle looks stuck.

### How availability is determined

`GET /api/system/status` `camera.available` means a camera is **registered** and not in an error state. It does not open the device. A real open happens only on `POST /api/cameras/{id}/start` or `scripts/test_webcam.py`.

## Development flow (Phase 2)

1. Create/activate `backend/.venv`
2. `pip install -e ".[dev]"`
3. Copy `.env.example` to `.env`
4. `alembic upgrade head`
5. `pytest`, `ruff check .`, `ruff format --check .`, `mypy .`
6. `python -m app`
7. Hit `/api/health`, `/api/system/status`, `/api/cameras`
8. Optional: `.\.venv\Scripts\python.exe scripts/test_webcam.py`

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

After the pip install step, the backend does not call the network. Model download (Phase 3) is not part of this phase.
