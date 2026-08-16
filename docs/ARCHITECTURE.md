# Architecture (Phase 11)

Phase 11 hardens configuration, logging, camera/worker lifecycle, event retention,
and health/readiness without redesigning the vision pipeline.

**Preserved:** CameraSource, size-1 latest-frame slot, DetectionWorker, YuNet/SFace,
gallery recognition, EventService, SQLite, FastAPI, Next.js, TanStack Query.

**TEST ONLY** recognition harness (`RECOGNITION_TEST_MODE`, default `false`): see
`docs/RECOGNITION_TESTING.md`.

## Runtime

```text
USB Webcam (UsbCameraSource)
    → LatestFrameSlot (size 1)
    → DetectionWorker (interval-gated, non-daemon)
    → YuNet → Tracker → Quality → Align → SFace → Recognition
    → EventService (cooldown + optional retention purge on startup)
    → SQLite

Enrollment sessions → latest_embeddings → EnrollmentService

npm run dev
    → concurrently
        → uvicorn :8000
        → next dev :3000  (/backend proxy → :8000)
```

## Failure handling (Phase 11)

- Consecutive capture read failures → camera `ERROR` (device released)
- `CAMERA_RECOVER_ON_START`: Start performs close → open → start (no background loop)
- Detection worker clears `_running` on loop exit; stop joins the thread
- `/api/health` = liveness; `/api/ready` = DB + models (camera not required)

## Docs

| Doc | Topic |
| --- | --- |
| `docs/OPERATIONS.md` | Runbook, retention, recovery |
| `docs/SECURITY.md` | Local security model |
| `docs/TESTING.md` | Automated / hardware / E2E |
| `docs/TROUBLESHOOTING.md` | Common failures |
| `docs/SETUP.md` | Install |
| `docs/ACCEPTANCE_TEST.md` | Acceptance report |
| `docs/RECOGNITION_TESTING.md` | Webcam-free recognition tests |
