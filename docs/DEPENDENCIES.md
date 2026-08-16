# Dependencies (Phase 7A)

Python package versions are pinned in `backend/pyproject.toml`. Licenses below were taken from the projects’ official packaging metadata / repositories. This is not legal advice.

AI **model** licenses are recorded in `docs/MODELS.md`. Package licenses here are for the Python wheels, not for YuNet weights.

There are **no** cloud AI, telemetry, or paid API dependencies.

## Runtime

| Package | Version | License | Why it is included |
| --- | --- | --- | --- |
| FastAPI | 0.141.1 | MIT | HTTP API |
| Starlette | (FastAPI dependency) | BSD-3-Clause | ASGI / TestClient stack |
| Uvicorn | 0.52.3 | BSD-3-Clause | ASGI server (`[standard]` extras for reload/httptools) |
| Pydantic | 2.13.4 | MIT | Request/response schemas |
| pydantic-settings | 2.15.0 | MIT | Environment / `.env` settings |
| python-dotenv | 1.2.2 | BSD-3-Clause | `.env` file loading used by pydantic-settings |
| SQLAlchemy | 2.0.52 | MIT | ORM / engine (2.x APIs only); Person + enrollment persistence |
| Alembic | 1.19.1 | MIT | Schema migrations (`persons`, `enrollment_samples`) |
| greenlet | (SQLAlchemy dependency) | MIT | SQLAlchemy 2 support |
| NumPy | 2.5.2 | BSD-3-Clause | Frames, YuNet decode, coordinate mapping |
| opencv-python | 5.0.0.93 | Apache-2.0 | USB `VideoCapture`, resize/pad, preview drawing |
| onnxruntime | 1.28.0 | MIT | CPU inference (`CPUExecutionProvider` only) for YuNet + SFace |

**ONNX Runtime:** `onnxruntime==1.28.0` is the CPU wheel. Do **not** install `onnxruntime-gpu`. The engine passes `providers=["CPUExecutionProvider"]` and checks that this provider is active.

**OpenCV choice:** camera capture, resize/pad, affine align, preview drawing — not the DNN runtime for YuNet/SFace.

All of the above were selected for **Python 3.13** on Windows 11 (primary tested). The same pins are intended for Ubuntu LTS with Python 3.13.

## Development

| Package | Version | License | Why it is included |
| --- | --- | --- | --- |
| pytest | 9.1.1 | MIT | Tests |
| pytest-asyncio | 1.4.0 | Apache-2.0 | Async pytest mode (`asyncio_mode = auto`) |
| httpx | 0.28.1 | BSD-3-Clause | Required by FastAPI/Starlette `TestClient` |
| Ruff | 0.16.3 | MIT | Lint + format |
| mypy | 2.3.1 | MIT | Static typing |

## Explicitly not included (Phase 7A)

| Package | Reason |
| --- | --- |
| onnxruntime-gpu | CPU-only machine; GPU providers are out of scope |
| insightface | Pretrained weights are **not suitable for commercial use** |
| Redis / Celery | Not needed for one local process |
| PostgreSQL drivers | SQLite only |
| Docker | Native Windows/Linux is the run path |

## Known warnings

Starlette 1.6 (pulled in by FastAPI 0.141.1) emits:

```text
StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
```

`httpx` remains because that is FastAPI’s current TestClient stack and the tests pass. Do not treat this warning as a test failure. Revisit when FastAPI/Starlette document a stable `httpx2` migration.

Application source in this repository is original. Third-party packages remain under their own licenses. Preserve notices if you redistribute wheels or vendored files.
