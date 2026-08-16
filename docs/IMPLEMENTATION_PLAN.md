# Implementation Plan — Local-First Face Recognition Camera System

**Phase:** 0 (Repository analysis only)  
**Date:** 2026-08-16  
**Status:** Plan complete. No application code has been written. Implementation starts at Phase 1 after this document is accepted.

This document is the Phase 0 deliverable. It records what exists in the repository today, the verified technology and model choices, the architecture that later phases will implement, and the gated phase sequence.

---

## 1. Repository analysis

### 1.1 Current state

The workspace `d:\project\ai\test3-img-prs` is **empty**.

| Check | Result |
| --- | --- |
| Files | 0 |
| Directories (other than `.` / `..`) | 0 (this `docs/` folder was created only to hold this plan) |
| Git repository | No (`.git` is absent) |
| Existing frontend | None |
| Existing backend | None |
| Package managers / lockfiles | None |
| Tests | None |
| Conventions | None — this is a greenfield project |
| Docker / CI | None |
| README | None |

There is **no working application to preserve**. Later phases will create the monorepo from scratch. There is no unrelated code to avoid rewriting.

### 1.2 Local development machine (verified)

| Item | Value |
| --- | --- |
| OS | Windows 11 (`win32 10.0.26200`) |
| CPU / RAM (target) | Intel Core i7-13700H, 16 GB, no dedicated GPU |
| Python | 3.13.1 (`python` / `py`) |
| Node.js | v24.18.1 |
| npm | 11.16.0 |
| pnpm | Not installed |
| Git | 2.45.2.windows.1 |
| OpenCV currently installed | No |

**Package-manager decision:**

- Python: `pyproject.toml` + virtualenv + pip (no Poetry/uv required).
- Frontend: **npm** (already present). Do not introduce pnpm.

### 1.3 Verified library versions (PyPI / GitHub, 2026-08-16)

These are the versions that Phase 1 will pin after a Windows + Python 3.13 install check. Do not treat them as already installed.

| Package | Latest verified | Notes |
| --- | --- | --- |
| FastAPI | 0.141.1 | Pydantic v2 |
| Pydantic | 2.13.4 | |
| pydantic-settings | 2.15.0 | YAML + `.env` |
| SQLAlchemy | 2.0.52 | 2.0 `Mapped` style |
| Alembic | 1.19.1 | |
| ONNX Runtime (PyPI) | 1.28.0 | CPU package `onnxruntime` only. Do not install `onnxruntime-gpu`. |
| OpenCV (PyPI) | 5.0.0.93 | Major 5.x. Last 4.x on the same index observed: 4.9.0.80. Phase 1 must confirm a Python 3.13 wheel and Windows `VideoCapture` (MSMF/DirectShow). Prefer `opencv-python-headless`. |
| Next.js | 16.3.1 (GitHub release 2026-08-13) | App Router |
| TanStack Query | v5 (install latest 5.x) | Server state |

Lint / test tools (to be added in the matching phase):

- Backend: `ruff`, `mypy`, `pytest`, `pytest-asyncio`, `httpx`
- Frontend: ESLint, TypeScript `tsc`, Vitest, Testing Library
- E2E: Playwright (Phase 10)

If OpenCV 5.0 has Windows webcam regressions, pin the newest 4.x wheel that supports Python 3.13 and document the fallback in `docs/TROUBLESHOOTING.md`. Do not mix OpenCV DNN inference with ONNX Runtime inference for the same model.

---

## 2. Product and architecture decisions

### 2.1 Scope of v1

In scope: one USB webcam, local CPU inference, person enrollment, face detection/tracking/recognition, events with cooldown, optional snapshots (off by default), REST + WebSocket UI.

Explicitly **out of scope** for v1 (interfaces only):

- RTSP / IP cameras, video files, HTTP cameras
- Multiple simultaneous camera workers
- Vehicle / license-plate detection and OCR
- Video recording
- GPU / CUDA / TensorRT / OpenVINO execution providers
- PostgreSQL, Redis, object storage (S3/Azure)
- Cloud AI APIs, telemetry, paid services

### 2.2 Detection vs recognition (product rule)

| Stage | Responsibility |
| --- | --- |
| Face detection | “A face exists here” (box, landmarks, detector score) |
| Face recognition | “This face matches a registered person above threshold” |

If cosine similarity is below the configured threshold, the result is **`Unknown`**. The matcher must never force an unknown face onto the nearest registered person.

Similarity is **not** a calibrated probability. The UI and API will label it as `similarity` (cosine), not `probability`.

### 2.3 High-level runtime

```text
USB webcam
    → UsbCameraSource (capture thread, bounded latest-frame buffer)
    → MJPEG preview endpoint (no AI)
    → FrameProcessor (interval + resize)
         → FaceDetector (YuNet / ONNX Runtime)
         → FaceTracker (IoU tracker, no extra model)
         → FaceEmbedder (SFace / ONNX Runtime)  [new/updated tracks only]
         → FaceMatcher (in-memory cosine vs registered embeddings)
         → EventEngine (cooldown / debounce)
              → EventRepository (SQLite)
              → optional LocalStorageProvider snapshot
              → WebSocket fan-out
```

Frontend talks only to REST + WebSocket + MJPEG. **No inference in the browser.**

### 2.4 Future-proofing without implementing the future

| Extension point | v1 implementation | Later without rewrite |
| --- | --- | --- |
| `VideoSource` | `UsbCameraSource` | `RtspCameraSource`, `FileVideoSource`, `HttpCameraSource` |
| `InferenceEngine` | ONNX Runtime `CPUExecutionProvider` | CUDA / TensorRT / OpenVINO via session providers |
| `DetectionEngine` | `FaceDetectionEngine` | `VehicleDetectionEngine`, `PlateDetectionEngine` |
| `RecognitionEngine` | `FaceRecognitionEngine` | `PlateOCR` |
| `EmbeddingIndex` | In-process numpy cosine | pgvector / external ANN |
| `StorageProvider` | `LocalStorageProvider` | S3 / Azure Blob |
| `Event.event_type` | face_* only | `vehicle_detected`, `plate_detected`, `plate_recognized` |
| Database URL | SQLite | PostgreSQL via SQLAlchemy URL + Alembic |

Do not add Redis, Celery, or extra processes in v1. One capture thread + one processing thread + FastAPI is enough for one webcam.

---

## 3. Model selection (license-first)

Official repositories and licenses were checked **before** choosing models. Code licenses and pretrained-weight licenses are treated as separate.

### 3.1 Selected models (v1)

| Role | Model | Version | Source | License | Commercial use |
| --- | --- | --- | --- | --- | --- |
| Face detection + 5 landmarks | YuNet | `face_detection_yunet_2023mar.onnx` | [opencv/opencv_zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) | **MIT** (directory LICENSE) | Allowed |
| Face embedding | SFace | `face_recognition_sface_2021dec.onnx` | [opencv/opencv_zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface) | **Apache-2.0** (directory LICENSE) | Allowed |

These two are the official OpenCV Zoo pairing. YuNet supplies the 5 landmarks SFace alignment expects.

**Download (avoid Git LFS pointer files):**

- Hugging Face: `opencv/face_detection_yunet`, `opencv/face_recognition_sface`
- SHA-256 to verify in the download script:
  - YuNet 2023mar: `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4` (232,589 bytes ≈ 227 KB)
  - SFace 2021dec: `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79` (≈ 38.7 MB)

**CPU fit:** Combined weights are ~39 MB. Both are designed for CPU. This is appropriate for an i7-13700H with 16 GB RAM.

**Expected I/O:**

- YuNet: resized BGR frame (v1 default input 320×320), output boxes + 5 landmarks + scores
- SFace: aligned 112×112 face crop → **128-d** embedding (L2-normalized)

Phase 3/4 will document measured latency on this machine in `docs/MODELS.md`.

### 3.2 Rejected models

#### InsightFace `buffalo_*` / `antelopev2` (including `buffalo_l`)

| Field | Value |
| --- | --- |
| Official repo | [deepinsight/insightface](https://github.com/deepinsight/insightface) |
| Code license | MIT (commercial code use allowed) |
| **Pretrained model license** | Non-commercial research only |
| Maintainer statement | Issue [#2486](https://github.com/deepinsight/insightface/issues/2486): “all open source models from our repo are for non-commercial research purposes only.” README (updated 2025-11-24) directs commercial licensing to `recognition-oss-pack@insightface.ai`. |

```text
NOT SUITABLE FOR COMMERCIAL USE
```

Do **not** silently ship InsightFace pretrained weights. Do not add the `insightface` Python package as a runtime dependency (it auto-downloads those weights).

#### Other rejected options

| Option | Why not for v1 |
| --- | --- |
| YuNet `2026may` dynamic-shape export | Useful later; v1 will use the well-documented 2023mar file at a fixed 320×320 for predictable CPU cost |
| SFace INT8 | Accuracy is close; skip until Phase 11 measurements justify it |
| MediaPipe face models | Apache-2.0, but adds a second ecosystem; YuNet+SFace already cover detect+embed |
| dlib / face_recognition | Weaker accuracy, extra native build pain on Windows, not ONNX Runtime |

Phase 4 documentation (`docs/MODELS.md`) will repeat the full model cards required by the product spec.

### 3.3 Inference design

ONNX Runtime is the **only** inference backend in v1.

```text
InferenceEngine (Protocol)
    └── OnnxRuntimeEngine
            providers = ["CPUExecutionProvider"]   # v1
            # future: CUDAExecutionProvider, TensorrtExecutionProvider, OpenVINOExecutionProvider
```

- Session creation, input/output names, and warmup live behind `InferenceEngine`.
- Core services must not import CUDA packages.
- OpenCV is used for `VideoCapture`, resize, color convert, affine align, and JPEG encode — not as the DNN runtime for these models.
- One detector session and one embedder session for the process (no per-request model load).

YuNet post-processing and SFace 5-point alignment will be implemented as small, tested Python modules (reference: OpenCV Zoo demos, MIT/Apache). Do not vendor InsightFace code.

---

## 4. Processing defaults (CPU-first, to be measured)

Real-time FPS is not a goal. Defaults below are starting points for an i7-13700H. Phase 11 overwrites them only after measurement.

```yaml
camera:
  default_source: 0
  capture_backend: dshow    # Windows DirectShow; MSMF fallback documented
  capture_width: 640
  capture_height: 480
  capture_fps: 15

processing:
  detection_interval_ms: 400
  recognition_interval_ms: 2000
  tracking_interval_ms: 100   # cheap IoU update on latest frame
  max_frame_width: 640
  max_frame_height: 480
  detector_input_width: 320
  detector_input_height: 320
  max_faces: 10
  frame_queue_size: 2         # drop oldest (backpressure)

recognition:
  threshold: 0.363            # OpenCV SFace LFW cosine (same identity if similarity >= threshold)
  min_face_size: 40           # pixels on processed frame
  min_detector_score: 0.6
  embeddings_per_person: 5

events:
  save_snapshot: false
  recognition_cooldown_seconds: 5
  unknown_cooldown_seconds: 5
  face_detected_cooldown_seconds: 10
```

**Why 0.363:** OpenCV’s SFace tutorial reports LFW cosine threshold **0.363** (same identity if cosine similarity ≥ 0.363). This is a similarity cutoff, not a probability. Calibration guidance will live in `docs/MODELS.md` and the Settings UI:

1. Enroll 3–5 samples of a known person.
2. Observe similarity of the same person across lighting/pose.
3. Observe similarity of a different person.
4. Set threshold between those two clusters; raise it to reduce false accepts.

**Separate rates:**

| Rate | Typical v1 behavior |
| --- | --- |
| Camera FPS | Capture loop, ~15 FPS into a size-2 “latest frame” slot |
| Tracking FPS | Up to ~10 Hz IoU association, no neural net |
| Detection FPS | ~2.5 Hz (`detection_interval_ms: 400`) |
| Recognition FPS | New track immediately; existing tracks at `recognition_interval_ms` |

---

## 5. Backend design

### 5.1 Layout

```text
backend/
  app/
    main.py
    api/                 # thin routers only
    core/                # config, logging, exceptions, security
    db/                  # engine, session, base
    models/              # SQLAlchemy
    schemas/             # Pydantic API schemas (never expose ORM)
    repositories/
    services/
    vision/              # InferenceEngine, detectors, embedders, tracker, matcher, pipeline
    cameras/             # VideoSource, UsbCameraSource, CameraManager
    events/              # EventEngine, cooldown, websocket hub
    storage/             # StorageProvider
  alembic/
  tests/
  pyproject.toml
```

Business logic stays in services. Routers validate input, call a service, return a schema.

### 5.2 Configuration

- `config.yaml` — defaults (committed)
- `.env` / `.env.example` — overrides (`DATABASE_URL`, `CORS_ORIGINS`, log level)
- `pydantic-settings` loads YAML then env. Single `Settings` object. No duplicated constants.

CORS: development allowlist `http://localhost:3000`. Production must not use `*`.

### 5.3 Database (SQLite first)

SQLAlchemy 2.0 + Alembic. No raw SQL in application code.

**Entities**

- `Camera` — `id`, `name`, `source_type`, `source_config` (JSON; not returned in full if it later contains credentials), `enabled`, timestamps
- `Person` — `id`, `name`, timestamps
- `FaceEmbedding` — `id`, `person_id`, `embedding` (BLOB of float32), `quality_score`, timestamps
- `Event` — `id`, `event_type`, `camera_id`, `person_id` (nullable), `similarity` (nullable), `timestamp`, `snapshot_path` (nullable), `metadata_json`
- `SystemSetting` — key/value for runtime-tunable settings (threshold, snapshot flag) that the Settings UI can change without restart where safe

**Indexes:** `Event.timestamp`, `Event.camera_id`, `Event.person_id`, `Event.event_type`, plus `(event_type, timestamp)` for filtered lists.

Embeddings are **not** stored in a vector extension. `EmbeddingIndex` protocol:

- v1: load all embeddings into memory on start / person change; numpy cosine
- later: PostgreSQL / pgvector implementation of the same protocol

### 5.4 Camera lifecycle

`CameraManager` owns sources.

```text
start → open device → capture thread → processing attached
stop  → stop processing → release VideoCapture → join thread (timeout)
restart = stop + start
shutdown = stop all (FastAPI lifespan)
```

Windows-specific: open with `cv2.CAP_DSHOW` first. Handle busy device, invalid index, disconnect (read failures → status `disconnected`, emit system event, do not spin unbounded retries without backoff).

Bounded buffers only: latest-frame slot (size 1) for preview; processing queue size 2 with drop-oldest.

### 5.5 Face pipeline modules (uncoupled)

```text
FaceDetector
FaceTracker
FaceAligner
FaceEmbedder
FaceMatcher
```

Tracker v1: IoU + centroid ID assignment (SORT-like, no Kalman required at one webcam). Track ID is the identity used for event cooldown while the face remains visible.

Matcher: max cosine over that person’s embeddings; if `max_similarity < threshold` → `Unknown` with `person_id = null`.

### 5.6 Events

Initial `event_type` values (string enum, extensible):

- `face_detected`
- `person_recognized`
- `unknown_person_detected`

Cooldown key: `(camera_id, track_id, event_type, person_id or "unknown")`. While the same track stays alive, suppress duplicates until `recognition_cooldown_seconds` elapses. New track ID after a gap can emit again. Document this in `docs/ARCHITECTURE.md`.

Snapshots: default **off**. If on, `LocalStorageProvider` writes under `storage.path` with a sanitized event-id filename (no path traversal). Store relative path on the event.

### 5.7 API (thin)

REST as specified (`/api/health`, `/api/system/status`, cameras CRUD + start/stop, people CRUD + enroll, events list/detail). Event list: pagination + `camera`, `person`, `event_type`, `from`, `to`.

Live preview: `GET /api/cameras/{id}/preview` **MJPEG**. Not WebSocket, not raw frames on `/ws/events`.

WebSocket: `/ws/events` — typed JSON `{ type, event }`. Server → client only for v1 (ignore/validate unexpected client messages). Heartbeat + application-level close on shutdown.

Enrollment: `POST /api/people/{id}/enroll` accepts one or more JPEG frames (or a capture-from-running-camera action). Backend detects, quality-filters, embeds, stores embeddings. Do not keep full enrollment images by default.

### 5.8 Logging

Standard `logging` with structured fields (`logger`, `camera_id`, `event_type`). Named loggers:

- `app`
- `app.vision`
- `app.camera`
- `app.events`

Never log embeddings, raw images, or future camera credentials.

### 5.9 Errors

Central FastAPI exception handlers → `{ "error": { "code", "message", "details" } }` with proper HTTP status. Camera, model-load, and DB failures are first-class error codes. Do not swallow exceptions.

### 5.10 Health

`GET /api/health` — process up, DB reachable.  
`GET /api/system/status` — CPU/RAM (psutil), camera states, model loaded, last inference latency, queue depth, processing enabled.

---

## 6. Frontend design

### 6.1 Layout

Next.js App Router + TypeScript + Tailwind CSS + shadcn/ui.

```text
frontend/
  app/
    dashboard/
    cameras/
    people/
    events/
    settings/
    system/
  components/
  features/
  lib/          # API client, WS client, query keys
  hooks/
  types/
  tests/
```

### 6.2 State

- TanStack Query for all server data (cameras, people, events, system status).
- Local React state for forms, dialogs, selected camera.
- Zustand **only** if needed for WebSocket connection status / latest live detections that multiple widgets share. Do not put REST caches in Zustand.

### 6.3 Pages (v1)

| Route | Contents |
| --- | --- |
| `/dashboard` | Camera status, MJPEG preview, current faces / recognized name, recent events, CPU/RAM, AI status |
| `/cameras` | List, add USB camera (index + name), start/stop, unavailable state |
| `/people` | List, add name, enroll from webcam, embedding count, delete |
| `/events` | Filters, pagination, similarity, snapshot if present |
| `/settings` | Threshold, snapshot flag, cooldown, processing intervals (via API) |
| `/system` | Health, model versions, camera backend, logs pointer |

Loading / empty / error / retry on every data view. WebSocket reconnect with backoff. Camera unavailable is a visible state, not a blank preview.

### 6.4 Preview

`<img src="{api}/api/cameras/{id}/preview">` (MJPEG). Overlay of current detections can come from a lightweight REST poll or WS `face_update` message **without** image bytes (boxes + labels only). Prefer WS metadata + MJPEG for v1.

---

## 7. Project structure (monorepo)

```text
project-root/
├── frontend/
├── backend/
├── models/                 # gitignored ONNX files; SHA checksums committed
├── data/                   # gitignored db + snapshots
├── docs/
│   ├── IMPLEMENTATION_PLAN.md   # this file
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── DEPENDENCIES.md
│   ├── MODELS.md
│   ├── SETUP.md
│   └── TROUBLESHOOTING.md
├── scripts/
│   └── download_models.py
├── .env.example
├── README.md
├── docker-compose.yml      # optional; native Windows is the primary path
└── .gitignore
```

Docker Compose will exist for documentation/parity but **will not** be the primary run mode: USB webcam passthrough on Windows Docker is unreliable. README will say: run backend and frontend natively on Windows 11.

---

## 8. Testing strategy

AI numeric outputs will **not** be asserted as exact model logits.

| Layer | Approach |
| --- | --- |
| Unit | Matcher threshold, cooldown, embedding dim/serialization, path sanitization, VideoSource fake |
| Camera | Fake `VideoSource` with fixture frames; lifecycle start/stop/cleanup |
| API | httpx + SQLite tempfile |
| Vision | Synthetic embeddings; optional ONNX smoke test marked `integration` if models are present |
| Frontend | Component tests for empty/error/loading; API client mocks |
| E2E (Phase 10) | Playwright; may stub camera/pipeline via test fixtures / test mode so CI does not require a physical face |

Phase 10 critical journey (local with webcam, CI with stubs):

```text
Open dashboard → Add person → Enroll face → Start camera
→ Recognition / unknown → Event created → Event visible → Search
```

---

## 9. Phased implementation (gated)

**Rule:** After each phase, run that phase’s checks and fix failures before starting the next phase. Keep changes logically separated by phase.

### Phase 0 — Repository analysis — **COMPLETE**

- Inspected empty workspace and local toolchain.
- Verified model licenses.
- Produced this document.
- **Stop.** No application code.

### Phase 1 — Backend foundation

Implement FastAPI app skeleton: config, structured logging, SQLite, SQLAlchemy models, Alembic initial migration, exception handlers, `GET /api/health`, `GET /api/system/status` (CPU/RAM without cameras/models).

**Exit gate:** ruff, mypy, unit + integration tests for health/DB. Backend starts.

### Phase 2 — Camera abstraction

`VideoSource`, `UsbCameraSource`, `CameraManager`, camera REST, MJPEG preview, start/stop/restart/cleanup, disconnect handling.

**Exit gate:** fake-source unit tests; **manual** USB webcam open/close on this Windows machine. Do not continue until lifecycle is reliable.

### Phase 3 — Face detection

YuNet via `InferenceEngine` + ONNX Runtime CPU. Configurable interval and size. Boxes, landmarks, scores. Model health in `/api/system/status`.

**Exit gate:** tests with a fixture image (or skipped-if-no-model smoke); CPU usage note in `docs/MODELS.md`. Download script + checksums.

### Phase 4 — Face embeddings

`FaceEmbedder` (SFace), 128-d validation, serialization, `FaceEmbedding` persistence, `EmbeddingIndex`.

**Exit gate:** valid/invalid/dimension/serialization/DB tests.

### Phase 5 — Person registration

People CRUD + enroll API. Frontend People page: add name, capture from webcam, save embeddings, show enrollment count, delete.

**Exit gate:** API tests + manual enroll of one person.

### Phase 6 — Recognition

`FaceMatcher`, configurable threshold, Unknown path, pipeline wiring.

**Exit gate:** deterministic matcher tests; manual known vs unknown on webcam.

### Phase 7 — Event engine

Event persistence, cooldown, snapshot flag default false, event list filters/pagination.

**Exit gate:** unit + integration tests for dedup and snapshot-off default.

### Phase 8 — WebSocket

`/ws/events`, typed messages, connect/disconnect, frontend reconnect.

**Exit gate:** backend WS test + UI connection status.

### Phase 9 — Frontend dashboard and remaining pages

Dashboard, cameras, events, settings, system. Loading/error/empty. No inference on the client.

**Exit gate:** frontend lint, `tsc`, component tests.

### Phase 10 — E2E

Playwright critical journey. Fix failures before Phase 11.

### Phase 11 — Performance

Measure CPU, RAM, detect/embed latency, camera stability, model init time, event latency on the i7-13700H. Change intervals/sizes only from those numbers. Record in `docs/MODELS.md` / `docs/TROUBLESHOOTING.md`.

### Phase 12 — Final review

Architecture, security (path traversal, CORS, no secrets in git), dependency and license review, tests, docs (`README.md` + all `docs/*`). Clean-environment install from README.

---

## 10. Security (v1, local-only)

- Validate all API input with Pydantic.
- Sanitize snapshot paths; reject `..` and absolute escapes.
- Do not expose filesystem browse APIs.
- Do not return `source_config` secrets (USB index is fine; future RTSP passwords must be redacted).
- Restrict CORS; no wildcard in production config.
- `.env` gitignored; `.env.example` committed with dummy values.
- No telemetry, no cloud upload.

---

## 11. Documentation to be written in later phases

| File | When |
| --- | --- |
| `docs/IMPLEMENTATION_PLAN.md` | Phase 0 (this file) |
| `README.md` | Incremental; complete by Phase 12 |
| `docs/ARCHITECTURE.md` | Phases 1–7 as components land |
| `docs/SETUP.md` | Phase 1 + 3 (models) |
| `docs/API.md` | As endpoints are added |
| `docs/MODELS.md` | Phase 3–4 (full model cards + threshold calibration) |
| `docs/DEPENDENCIES.md` | Phase 1, updated when deps are added |
| `docs/TROUBLESHOOTING.md` | Phase 2 (camera) + Phase 11 (CPU) |

README must cover: requirements, Python/Node/model/DB setup, running backend/frontend, selecting a webcam, registering a person, recognition, tests, camera troubleshooting, CPU tuning. After install, the system must run **offline**.

---

## 12. Definition of done (tracked through Phase 12)

```text
[ ] Backend starts successfully
[ ] Frontend starts successfully
[ ] Webcam can be selected
[ ] Webcam can start/stop
[ ] Face detection works
[ ] Person can be registered
[ ] Face embedding is stored
[ ] Known person is recognized
[ ] Unknown person remains Unknown
[ ] Recognition threshold is configurable
[ ] Events are stored
[ ] Duplicate events are controlled
[ ] Snapshot saving is disabled by default
[ ] Events appear in realtime
[ ] Event search works
[ ] Camera disconnect is handled
[ ] Application shutdown releases camera
[ ] Unit tests pass
[ ] Integration tests pass
[ ] E2E tests pass
[ ] Lint passes
[ ] Type checks pass
[ ] Documentation is complete
[ ] Dependency licenses are documented
[ ] AI model licenses are documented
[ ] No cloud AI dependency exists
[ ] No paid service is required
```

All items are unchecked until the corresponding phase proves them.

---

## 13. Immediate next step

**Wait for confirmation, then start Phase 1 only.**

Phase 1 will:

1. Initialize git (if desired) and the monorepo skeleton.
2. Create `backend/` with FastAPI, config, logging, SQLite, Alembic, health/status.
3. Add `docs/DEPENDENCIES.md` (initial library licenses) and `.env.example`.
4. Run ruff, mypy, and tests, and fix all failures before Phase 2.
