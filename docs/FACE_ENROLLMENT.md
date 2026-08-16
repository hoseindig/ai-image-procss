# Face Enrollment (Phase 10)

Camera-driven enrollment reuses the existing backend vision pipeline. The browser never runs YuNet or SFace.

## Workflow

```text
Person (active)
  → POST /api/persons/{id}/enrollment-sessions
  → Camera must be RUNNING
  → DetectionRuntime latest snapshot
  → single face + quality.accepted + aligned + embedding
  → POST .../enrollment-sessions/{session_id}/capture
  → EnrollmentService.add_embedding (128-D blob in SQLite)
```

Raw vectors stay in-process (`DetectionRuntime.latest_embeddings`) and are written only through `EnrollmentService`. GET APIs never return vectors.

## API

| Method | Path | Role |
| --- | --- | --- |
| POST | `/api/persons/{id}/enrollment-sessions` | Start session (`camera_id` optional) |
| GET | `/api/persons/{id}/enrollment-sessions/{session_id}` | Poll state |
| POST | `/api/persons/{id}/enrollment-sessions/{session_id}/capture` | Persist sample when `ready` |
| DELETE | `/api/persons/{id}/enrollment-sessions/{session_id}` | Cancel |
| POST | `/api/persons/{id}/enrollments` | **Developer only** — precomputed vector |

### Session states

`starting` · `waiting_for_face` · `face_detected` · `multiple_faces` · `quality_rejected` · `ready` · `capturing` · `completed` · `failed` · `cancelled`

Capture is allowed only when:

- exactly one active track
- `quality.accepted == true`
- alignment succeeded
- embedding status `generated` and 128-D finite vector available
- person is active

Multiple faces → `multiple_faces` (no random pick).

Quality thresholds are **not** lowered for enrollment.

## Frontend

Person detail → **Enroll Face**:

- Starts/uses backend camera
- Shows MJPEG preview
- Polls session state
- Capture enabled only when `ready`
- Developer JSON paste is hidden behind “Show developer tools”

## Privacy

Sessions store metadata only (no frames/images). Logs may include `person_id`, `session_id`, `enrollment_id`, `track_id`, `camera_id` — never embeddings or pixels.

## Labels

| Item | Status |
| --- | --- |
| API + unit tests (fake camera/runtime) | **TESTED** |
| Windows UI enrollment with webcam | see E2E doc / manual verification |
| Linux webcam enrollment | **DOCUMENTED**, **NOT HARDWARE-TESTED** in Phase 10 |
