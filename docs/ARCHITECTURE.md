# Architecture (Phase 10)

Phase 10 adds **camera enrollment sessions** that capture embeddings from the live DetectionRuntime (same SFace path as recognition). Recognition threshold and cooldown defaults are unchanged.

## Runtime

```text
USB Webcam
    → DetectionWorker
    → YuNet → Tracker → Quality → Align → SFace → Recognition
    → EventService (cooldown)
    → SQLite events

Enrollment:
    → EnrollmentSessionService reads latest snapshot + latest_embeddings
    → EnrollmentService persists 128-D blob (no images)

Preview:
    → MJPEG /api/cameras/{id}/preview → Browser <img>
```

## Persistence

| Store | Contents |
| --- | --- |
| `persons` / `enrollment_samples` | Gallery embeddings (metadata on GET) |
| `events` | recognized / unknown_face audit rows |
| Enrollment sessions | In-memory only (TTL); no DB table |

## Selected API

| Method | Path | Role |
| --- | --- | --- |
| POST/GET/DELETE | `/api/persons/{id}/enrollment-sessions…` | Camera enrollment |
| POST | `/api/persons/{id}/enrollments` | Dev-only precomputed vector |
| GET | `/api/cameras/{id}/preview` | MJPEG |
| GET | `/api/events` | Paginated history |

## Docs

- `docs/FACE_ENROLLMENT.md`
- `docs/E2E_FACE_RECOGNITION.md`
- `docs/FRONTEND.md`
- `docs/EVENTS.md`
