# Architecture (Phase 8)

Phase 8 adds SQLite **recognition audit events** with cooldown deduplication. No video, snapshots, or frontend.

## Runtime

```text
USB Webcam
    → DetectionWorker
    → YuNet → Tracker → Quality → Align → SFace → Recognition
    → EventService (cooldown)
    → SQLite events
```

## Persistence

| Store | Contents |
| --- | --- |
| `persons` / `enrollment_samples` | Gallery (Phase 7A) |
| `events` | recognized / unknown_face audit rows (Phase 8) |

## API

| Method | Path | Role |
| --- | --- | --- |
| GET | `/api/cameras/{id}/detections` | live tracks + recognition metadata |
| GET | `/api/events` | paginated filtered event history |
| GET | `/api/events/{id}` | one event |
| * | `/api/persons…` | enrollment gallery |

## Docs

- `docs/EVENTS.md` — cooldown, schema, privacy, backup
- `docs/FACE_RECOGNITION.md` — matching
- `docs/PERSON_ENROLLMENT.md` — gallery
- `docs/MODELS.md` — model licenses
