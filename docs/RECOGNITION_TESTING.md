# Recognition Testing (TEST ONLY)

Deterministic **Known / Unknown / Event / Cooldown** tests that do **not** require
a USB webcam.

This is **not** liveness or anti-spoofing testing.

## Status categories (keep separate)

| Suite | Webcam | What it proves |
| --- | --- | --- |
| **Automated Recognition Tests** | No | Real SFace + gallery + threshold + events/cooldown |
| **Hardware Recognition Test** | Yes | Live/USB acceptance (`docs/ACCEPTANCE_TEST.md`) |
| **Browser E2E** | No | UI with mocked `/backend` (Playwright) |
| **Liveness / Anti-Spoofing** | — | **NOT TESTED** (out of scope) |

## Isolation / security

| Control | Behavior |
| --- | --- |
| `RECOGNITION_TEST_MODE` | Default **`false`**. Never auto-enabled on normal startup. |
| Webcam pipeline | Unchanged. DetectionWorker / MJPEG path is separate. |
| Quality gates | Unchanged (`FACE_QUALITY_MIN_SHARPNESS=60`, etc.). |
| API | `POST /api/test/recognize` returns **403** when mode is off. |
| Response | Never includes embeddings or image bytes. |
| Persistence | Does not store test images or embeddings (events only if `record_event`). |

Mark everything related as **TEST ONLY** in code (`tags=["test-only"]`, docs, scripts).

## Architecture

```
aligned 112×112 PNG/JPEG (synthetic fixture or crop)
    → RecognitionTestService (TEST ONLY, gated)
        → SFaceEmbedder.embed          (production)
        → GalleryFaceRecognizer.recognize (production threshold 0.363)
        → EventService.record_from_recognition (production cooldowns)
    → JSON status/similarity/event_id (no embedding)
```

Production webcam path remains: camera → YuNet → track → quality → align → SFace → gallery → events.

## Fixtures

Synthetic (not photographs), project-generated:

- `backend/tests/fixtures/faces/synthetic_aligned_a.png`
- `backend/tests/fixtures/faces/synthetic_aligned_b.png`

License/source: see `backend/tests/fixtures/faces/README.md`.

Regenerate:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\generate_recognition_fixtures.py
```

```bash
backend/.venv/bin/python backend/scripts/generate_recognition_fixtures.py
```

## Run automated recognition tests

### Windows PowerShell

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_recognition_testing.py tests/test_face_recognition.py tests/test_recognition_integration.py tests/test_events.py -q
```

Full backend suite:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy .
```

Or from repo root: `npm run test:all`

### Linux bash

```bash
cd backend
.venv/bin/python -m pytest tests/test_recognition_testing.py -q
.venv/bin/python -m pytest -q
```

Requires SFace ONNX at `models/face/sface/2021dec.onnx` for fixture embed tests.

## Optional TEST ONLY HTTP / CLI

Only for local debugging. Do **not** leave enabled.

```powershell
$env:RECOGNITION_TEST_MODE="true"
# start backend as usual, then:
curl.exe -F "file=@backend/tests/fixtures/faces/synthetic_aligned_a.png" `
  -F "camera_id=test" -F "track_id=1" `
  http://127.0.0.1:8000/api/test/recognize
```

CLI (process-local flag):

```powershell
backend\.venv\Scripts\python.exe backend\scripts\recognition_test.py `
  --force-test-mode `
  --image backend\tests\fixtures\faces\synthetic_aligned_a.png
```

```bash
backend/.venv/bin/python backend/scripts/recognition_test.py \
  --force-test-mode \
  --image backend/tests/fixtures/faces/synthetic_aligned_a.png
```

Enroll a person with a real embedding first if you expect `matched` (gallery must contain an active enrollment).

## Covered automated cases

| ID | Case |
| --- | --- |
| A | Enrolled synthetic face → recognized |
| B | Different synthetic face → unknown |
| C | Similarity below threshold → unknown |
| D | Similarity at threshold → recognized |
| E | Recognized event creation |
| F | Recognized cooldown |
| G | Unknown event creation |
| H | Unknown cooldown |
| I | Empty gallery |
| J | Inactive person ignored |
| + | Integration: embed → gallery → recognize → event |
| + | API 403 when `RECOGNITION_TEST_MODE=false` |
