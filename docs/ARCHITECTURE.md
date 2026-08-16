# Architecture (Phase 9)

Phase 9 adds a Next.js frontend that consumes the existing FastAPI face pipeline. Recognition behavior, thresholds, and cooldown defaults are unchanged.

## Runtime

```text
USB Webcam
    → DetectionWorker
    → YuNet → Tracker → Quality → Align → SFace → Recognition
    → EventService (cooldown)
    → SQLite events

Live frames also feed:
    → MJPEG /api/cameras/{id}/preview
    → Browser <img> (no getUserMedia for the main pipeline)

REST metadata:
    → Next.js /backend rewrite → FastAPI
    → TanStack Query → UI pages
```

## Persistence

| Store | Contents |
| --- | --- |
| `persons` / `enrollment_samples` | Gallery (Phase 7A) |
| `events` | recognized / unknown_face audit rows (Phase 8) |

No embeddings, snapshots, or video are stored by the frontend.

## API (selected)

| Method | Path | Role |
| --- | --- | --- |
| GET | `/api/health` | liveness |
| GET | `/api/system/status` | DB / camera / pipeline flags |
| GET/POST | `/api/cameras…` | lifecycle + detections |
| GET | `/api/cameras/{id}/preview` | MJPEG stream |
| * | `/api/persons…` | gallery |
| GET | `/api/events` | paginated filtered history |

## Frontend

See `docs/FRONTEND.md` for stack, RTL, proxy, and enrollment developer UI.

## Docs

- `docs/FRONTEND.md` — UI foundation
- `docs/EVENTS.md` — cooldown, schema, privacy
- `docs/FACE_RECOGNITION.md` — matching
- `docs/PERSON_ENROLLMENT.md` — gallery
- `docs/MODELS.md` — model licenses
