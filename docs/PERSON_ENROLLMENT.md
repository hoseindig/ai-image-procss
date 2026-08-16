# Person enrollment & face gallery (Phase 7A)

Phase 7A persists **Person** records and **enrollment embedding samples** in SQLite. Recognition/matching is Phase 7B (`docs/FACE_RECOGNITION.md`). This document covers gallery persistence only.

**Track ID ≠ Person ID.** Person IDs are UUID strings stored in the database.

## Prerequisites

- Python 3.13
- Backend virtualenv with `pip install -e ".[dev]"`
- SQLite file via `DATABASE_URL` (default `sqlite:///./data/app.db`, resolved from project root)

**Tested:** Windows 11 (this repo’s primary measured environment).  
**Documented:** Ubuntu LTS / Linux with the same commands (replace PowerShell with bash where noted).

## Database migration

From `backend/` with the virtualenv active:

```powershell
alembic upgrade head
```

Linux:

```bash
alembic upgrade head
```

Creates:

| Table | Purpose |
| --- | --- |
| `persons` | Persistent identity (`id`, `display_name`, `active`, timestamps) |
| `enrollment_samples` | Gallery embeddings + quality metadata (no images) |

Verify:

```powershell
alembic current
alembic downgrade 0001_initial
alembic upgrade head
```

## Embedding storage format

Each sample stores a **512-byte** `LargeBinary` blob:

- 128 × IEEE-754 **float32**
- **Little-endian**
- No header / length prefix / JSON

Codec: `app/persons/embedding_codec.py` (`serialize_embedding` / `deserialize_embedding`).

Validation before persist:

- exactly 128 dimensions
- all finite (no NaN / Inf)
- no silent reshape or truncate

## Person rules

- `display_name`: required, trimmed, non-empty, max 100 characters, unique
- `active`: default `true`
- `DELETE /api/persons/{id}` **deactivates** (soft); does not hard-delete the person or cascade-wipe audit intent
- Enrollment into an inactive person is rejected

## Enrollment rules

- Multiple samples per person are allowed; they are **not** averaged or auto-pruned
- Requires `quality.accepted == true` in the enrollment request
- Requires a valid 128-D embedding vector on **POST** only
- GET responses return **metadata only** (dimension, quality fields, ids, timestamps) — never the raw vector

## API examples

Create person:

```powershell
curl -X POST http://127.0.0.1:8000/api/persons -H "Content-Type: application/json" -d "{\"display_name\":\"Jane Doe\"}"
```

List persons:

```powershell
curl http://127.0.0.1:8000/api/persons
```

Enroll (embedding is write-only; produce it from the Phase 6 pipeline):

```powershell
curl -X POST http://127.0.0.1:8000/api/persons/{person_id}/enrollments -H "Content-Type: application/json" -d "{\"embedding\":[...128 floats...],\"normalized\":true,\"quality\":{\"accepted\":true,\"face_width\":120,\"face_height\":130,\"sharpness\":90,\"brightness\":110}}"
```

List enrollment metadata:

```powershell
curl http://127.0.0.1:8000/api/persons/{person_id}/enrollments
```

Deactivate person:

```powershell
curl -X DELETE http://127.0.0.1:8000/api/persons/{person_id}
```

Delete one enrollment sample:

```powershell
curl -X DELETE http://127.0.0.1:8000/api/persons/{person_id}/enrollments/{enrollment_id}
```

## Privacy

Face embeddings are biometric-sensitive.

- Do not log or print raw vectors
- Normal GET APIs never return the vector
- Logs may include `person_id`, `enrollment_id`, `dimension`, status — not the embedding
- Data stays local; no upload / telemetry

## Backup (SQLite)

Do **not** assume copying `data/app.db` while the app is writing is always safe.

Recommended approaches:

1. **Stop the backend**, then copy `data/app.db` (and any `-wal` / `-shm` if present after a clean close).
2. Or use the SQLite Online Backup API / `.backup` while ensuring a consistent snapshot:

```powershell
sqlite3 data\app.db ".backup 'data\app-backup.db'"
```

Linux:

```bash
sqlite3 data/app.db ".backup 'data/app-backup.db'"
```

Store backups with the same access controls as the live database (biometric data).

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `no such table: persons` | Run `alembic upgrade head` from `backend/` |
| 409 `person_conflict` | `display_name` already exists |
| 400 `enrollment_quality_rejected` | `quality.accepted` must be `true` |
| 400 `person_inactive` | Activate the person before enrolling |
| 400 `invalid_embedding` | Wrong dim / NaN / Inf |
| 422 on enroll | Request body failed schema validation (e.g. not 128 floats) |

## Known limitations

- Recognition/matching is Phase 7B (see `docs/FACE_RECOGNITION.md`)
- No frontend enrollment UI
- Enrollment POST accepts a precomputed embedding (pipeline boundary); no second image path
- Linux is documented; primary measured environment remains Windows 11
