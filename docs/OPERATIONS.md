# Operations (Phase 11)

Operational runbook for the single-camera, CPU-only local face system.

**TESTED:** Windows 11 startup via `npm run setup` / `npm run db:migrate` / `npm run dev` (prior phases; re-verify after config changes).  
**DOCUMENTED:** Linux bash equivalents (syntax-checked; Linux webcam **NOT HARDWARE-TESTED** in Phase 11).  
**OUT OF SCOPE:** GPU, PostgreSQL, Redis, WebSockets, video recording, liveness, plate recognition.

## Start / stop

### Windows (PowerShell)

```powershell
npm run setup
python scripts/download_models.py
npm run db:migrate
npm run dev
```

Ctrl+C stops backend and frontend (`concurrently`).

### Linux (bash)

```bash
npm run setup
python3 scripts/download_models.py
npm run db:migrate
npm run dev
```

| Service | URL |
| --- | --- |
| Frontend | http://127.0.0.1:3000 |
| Backend API | http://127.0.0.1:8000 |
| OpenAPI | http://127.0.0.1:8000/docs |

## Health vs readiness

| Endpoint | Meaning | Camera required? |
| --- | --- | --- |
| `GET /api/health` | **Liveness** — process is up | No |
| `GET /api/ready` | **Readiness** — DB reachable; required models loaded when features enabled | No |
| `GET /api/system/status` | Operational snapshot (includes `ready`) | Reports camera state only |

`/api/ready` returns **503** when not ready.

## Configuration (production-relevant)

Invalid values **fail fast** (no silent clamping). See `.env.example` and `docs/SETUP.md`.

Notable Phase 11 settings:

| Variable | Default | Notes |
| --- | --- | --- |
| `APP_ENV` | `development` | `development` \| `test` \| `production` |
| `DEBUG` | `true` | Must be `false` when `APP_ENV=production` |
| `RECOGNITION_TEST_MODE` | `false` | Must be `false` in production; gates `/api/test/recognize` |
| `EVENT_RETENTION_DAYS` | `90` | Purge on startup when enabled |
| `EVENT_RETENTION_ENABLED` | `true` | Does **not** delete people/enrollments |
| `CAMERA_RECOVER_ON_START` | `true` | From ERROR: close → open → start (not a background loop) |
| `CAMERA_MAX_CONSECUTIVE_READ_FAILURES` | `30` | Capture thread → ERROR after N failed reads |

Model path files must exist when detection/embedding are enabled and `APP_ENV` is not `test`.

## Event retention

On application startup, if `EVENT_RETENTION_ENABLED=true`, events with `occurred_at` older than `EVENT_RETENTION_DAYS` are deleted. Logged as:

`Event retention purge deleted=N retention_days=...`

People and face enrollments are never deleted by retention.

## Camera failure / recovery

1. Capture thread counts consecutive `VideoCapture.read()` failures.
2. After `CAMERA_MAX_CONSECUTIVE_READ_FAILURES`, state → `ERROR`, device is released.
3. Detection worker exits on camera read error (`_running` cleared).
4. User **Start** with `CAMERA_RECOVER_ON_START=true` performs close → open → start.
5. There is **no** aggressive background reconnect loop and **no** unbounded frame queue (size-1 latest-frame remains).

## Logging

Format: `timestamp | LEVEL | component | message`

Useful keys in messages: `camera_id`, `track_id`, `person_id`, `event_type`, `error_code`, durations.

**Never logged:** embeddings, raw images, secrets, credentials.

Per-frame recognition match/unknown and track create/remove are **DEBUG** (not INFO).

## Clean shutdown

Lifespan shutdown order: detection workers → camera manager → database dispose.

Threads are non-daemon. Join timeouts are bounded (~5s).

## Performance expectations (documented target)

**Hardware target (DOCUMENTED / prior measurements):** Intel i7-13700H, 16 GB RAM, CPU only, single USB webcam.

Pipeline (interval-gated, not every camera frame):

Camera → YuNet → Tracking → Quality → Alignment → SFace → Recognition → Events

Use existing benchmarks under `backend/scripts/benchmark_*.py` for local numbers. Do not treat them as SLAs.

## Known operational limits

- Single camera
- SQLite
- CPU only
- Hardware unknown-face recognition still **PARTIAL** without a second live face (see acceptance)
- Playwright Chromium install may be **BLOCKED** by network
