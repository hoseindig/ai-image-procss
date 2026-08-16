# Dependencies (Phase 9)

## Backend (Python)

Python package versions are pinned in `backend/pyproject.toml`. Licenses below were taken from the projects’ official packaging metadata / repositories. This is not legal advice.

AI **model** licenses are recorded in `docs/MODELS.md`.

There are **no** cloud AI, telemetry, or paid API dependencies.

### Runtime

| Package | Version | License | Why it is included |
| --- | --- | --- | --- |
| FastAPI | 0.141.1 | MIT | HTTP API |
| Starlette | (FastAPI dependency) | BSD-3-Clause | ASGI / TestClient stack |
| Uvicorn | 0.52.3 | BSD-3-Clause | ASGI server |
| Pydantic | 2.13.4 | MIT | Request/response schemas |
| pydantic-settings | 2.15.0 | MIT | Environment / `.env` settings |
| python-dotenv | 1.2.2 | BSD-3-Clause | `.env` loading |
| SQLAlchemy | 2.0.52 | MIT | ORM |
| Alembic | 1.19.1 | MIT | Migrations |
| NumPy | 2.5.2 | BSD-3-Clause | Frames / embeddings |
| opencv-python | 5.0.0.93 | Apache-2.0 | USB capture, JPEG encode for MJPEG |
| onnxruntime | 1.28.0 | MIT | CPU inference for YuNet + SFace |

**ONNX Runtime:** CPU wheel only. Do **not** install `onnxruntime-gpu`.

### Development

| Package | Version | License | Why |
| --- | --- | --- | --- |
| pytest | 9.1.1 | MIT | Tests |
| pytest-asyncio | 1.4.0 | Apache-2.0 | Async pytest |
| httpx | 0.28.1 | BSD-3-Clause | TestClient |
| Ruff | 0.16.3 | MIT | Lint + format |
| mypy | 2.3.1 | MIT | Typing |

## Frontend (Node)

Pinned via `frontend/package-lock.json`. Primary packages:

| Package | Role |
| --- | --- |
| next@15.5.2 | App Router UI |
| react / react-dom@19 | UI runtime |
| typescript | Types |
| tailwindcss@4 | Styling |
| @tanstack/react-query | Server state |
| @radix-ui/* + class-variance-authority + clsx + tailwind-merge + lucide-react | shadcn/ui primitives |
| vitest + Testing Library | Unit/component tests |
| @playwright/test | Optional E2E smoke |

**Node:** v24+ (tested: v24.18.1 on Windows 11).

## Explicitly not included

| Item | Reason |
| --- | --- |
| onnxruntime-gpu | CPU-only |
| insightface | Weight licensing unsuitable |
| Browser AI / ONNX in JS | Backend owns inference |
| WebSocket client libs | Polling + MJPEG for Phase 9 |
| Plate/OCR libraries | Future phases only |
| Redis / PostgreSQL / Docker as primary path | Local SQLite + native run |

## Known warnings

Starlette may emit an `httpx` / TestClient deprecation warning. Tests still pass; do not treat as failure.
