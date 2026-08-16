# Architecture (Phase 10.5)

Phase 10.5 adds **one-command** monorepo scripts (`npm run setup` / `dev` / `test:all`) without changing the vision pipeline.

## Runtime

```text
USB Webcam
    → DetectionWorker
    → YuNet → Tracker → Quality → Align → SFace → Recognition
    → EventService (cooldown)
    → SQLite events

Enrollment sessions → latest_embeddings → EnrollmentService

npm run dev
    → concurrently
        → uvicorn :8000
        → next dev :3000  (/backend proxy → :8000)
```

Recognition threshold and event cooldowns are unchanged.

## Docs

- `docs/ACCEPTANCE_TEST.md` — hardware acceptance
- `docs/FACE_ENROLLMENT.md`
- `docs/FRONTEND.md`
- `docs/SETUP.md`
