# Events & audit logging (Phase 8)

Phase 8 persists lightweight **recognition audit events** in SQLite. It does **not** store embeddings, images, video, or continuous frames. No video recording. No snapshots by default.

## Architecture

```text
RecognitionResult
    → EventService (cooldown / dedupe)
    → EventRepository
    → SQLite events
```

Application code must not write the `events` table directly.

## Event types

| Type | When |
| --- | --- |
| `recognized` | `RecognitionResult.status == matched` |
| `unknown_face` | `RecognitionResult.status == unknown` |

Extensible enum also reserves `track_started` / `track_lost` (not emitted yet).

## Cooldown / deduplication

| Event | Cooldown key | Default |
| --- | --- | --- |
| recognized | `camera_id + person_id` | `EVENT_RECOGNIZED_COOLDOWN_SECONDS=10` |
| unknown_face | `camera_id + track_id` | `EVENT_UNKNOWN_COOLDOWN_SECONDS=10` |

**Why different keys:** Person ID is persistent; Track ID is process-local and resets when workers restart. Recognized spam control must use Person ID so Track ID changes do not create duplicate events for the same person during cooldown. Unknown faces have no Person ID, so Track ID + camera is used.

Cooldowns are **in-memory** (not DB). Different people / cameras are not globally suppressed.

`EVENT_RETENTION_DAYS` is configured for a future cleanup job; **automatic deletion is not implemented** in Phase 8.

## Schema

Table `events`:

- `id` (UUID string)
- `event_type`
- `camera_id`
- `track_id` (runtime tracing only)
- `person_id` (nullable)
- `enrollment_id` (nullable)
- `similarity` (nullable score, not a percentage)
- `occurred_at` / `created_at` (UTC)

Indexes:

| Index | Purpose |
| --- | --- |
| `ix_events_occurred_at` | Newest-first listing |
| `ix_events_camera_occurred` | Filter by camera + time |
| `ix_events_person_occurred` | Filter by person + time |
| `ix_events_type_occurred` | Filter by type + time |

Migration: `0003_events`.

## API

```text
GET /api/events?camera_id=&person_id=&event_type=&from=&to=&page=1&page_size=50
GET /api/events/{event_id}
```

Offset pagination. Default page size 50; max 200 (`EVENT_API_*`). Order: `occurred_at DESC`, then `id DESC`.

Never returns embeddings or images.

## Webcam

```powershell
.\.venv\Scripts\python.exe scripts/test_webcam.py --show-recognition --log-events --log-quality
```

## Privacy

**Stored:** event metadata (ids, type, similarity, timestamps).  
**Not stored:** embeddings, frames, images, video.

Events can still identify people. Protect `data/app.db` with OS permissions. Backup with SQLite `.backup` or stop the app first — do not blindly copy a live DB file.

## Security

Face recognition is not authentication. Events are sensitive audit data. Similarity is a mathematical score.

## Known limitations

- Synchronous SQLite writes from the vision path (acceptable for one camera / small event rate; measured in `benchmark_events.py`)
- No automatic retention purge
- No snapshots / video
- Linux documented; primary measured environment is Windows 11

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `no such table: events` | `alembic upgrade head` |
| Event spam | Lower cooldown is too small; raise `EVENT_*_COOLDOWN_SECONDS` |
| No events | `EVENT_LOGGING_ENABLED`; recognition must be matched/unknown |
| 400 page_size | Exceeds `EVENT_API_MAX_PAGE_SIZE` |
