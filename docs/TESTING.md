# Testing (Phase 11)

## Automated (no webcam required)

### Backend

```bash
cd backend
# Windows: .\.venv\Scripts\activate
# Linux: source .venv/bin/activate
pytest
ruff check .
ruff format --check .
mypy .
```

### Frontend

```bash
cd frontend
npm test
npm run lint
npm run typecheck
npm run build
```

### Monorepo

```bash
npm run test:all
```

## Recognition without webcam

See `docs/RECOGNITION_TESTING.md`.

```bash
cd backend
pytest tests/test_recognition_testing.py -q
```

`RECOGNITION_TEST_MODE` stays **false** for normal `npm run dev`.

## Browser E2E (Playwright)

```bash
cd frontend
npx playwright install chromium   # may be BLOCKED by CDN/network
npm run frontend:e2e
```

If Chromium cannot be installed/downloaded: report **BLOCKED**, do not claim PASS.

E2E stubs the backend; it does **not** prove hardware recognition.

## Hardware / manual camera

See `docs/ACCEPTANCE_TEST.md`.

Requires a real USB webcam and exclusive device access.

## Phase 11 regression focus

| Area | Tests |
| --- | --- |
| Config fail-fast | `tests/test_config.py` |
| USB read → ERROR | `tests/test_phase11_hardening.py` |
| Start/stop cycles, worker shutdown | `tests/test_phase11_hardening.py` |
| Event retention | `tests/test_events.py` |
| Health / ready | `tests/test_health.py` |

## Honesty labels

Use these in reports:

- **TESTED** — executed in this environment
- **DOCUMENTED** — instructions written; not executed here
- **NOT HARDWARE-TESTED** — needs physical camera/person
- **BLOCKED** — external dependency or environment prevented the run
- **PARTIAL** — incomplete evidence
