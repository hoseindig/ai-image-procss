# Acceptance Test (Phase 10.5)

Manual **Hardware E2E** acceptance checklist for the integrated face-recognition system.

This is **not** the Playwright browser suite. Playwright uses a mocked backend and does **not** prove webcam recognition.

| Suite | Webcam | AI | Purpose |
| --- | --- | --- | --- |
| Automated Recognition Tests (`docs/RECOGNITION_TESTING.md`) | No | Real SFace + gallery | Known/Unknown/Events without hardware |
| Automated (`npm run test:all`) | No | Fake/unit + recognition tests | Regressions |
| Browser E2E (Playwright) | No | Mocked API | UI wiring |
| **This document** | **Yes** | **Real pipeline** | Hardware acceptance |
| Liveness / Anti-Spoofing | — | — | **NOT TESTED** |

**Threshold:** `FACE_RECOGNITION_THRESHOLD=0.363` (do not change). Show similarity as `0.xxx`, never as a percentage.

**Cooldowns (defaults):** `event_recognized_cooldown_seconds=10.0`, `event_unknown_cooldown_seconds=10.0`.

Hardware unknown-person gaps can be covered for CI by **Automated Recognition Tests** (synthetic fixtures). That does **not** replace this hardware checklist for live webcam acceptance.

---

## Prerequisites

1. `npm run setup`
2. `python scripts/download_models.py` (once)
3. `npm run db:migrate`
4. USB webcam connected
5. `npm run dev`
6. Open http://127.0.0.1:3000

---

## A. System

- [ ] Frontend loads
- [ ] Dashboard shows backend health **ok**
- [ ] System status: database connected
- [ ] Camera available (registered; may be stopped)

## B. Person creation

- [ ] Create person **Test Person A**
- [ ] Person appears in `/people`

## C. Enrollment (real webcam)

- [ ] Open Test Person A → **Enroll Face**
- [ ] Camera starts / MJPEG visible
- [ ] Exactly **one** face in frame
- [ ] State progresses past waiting / quality issues to **ready**
- [ ] Capture succeeds
- [ ] Enrollment count increases

If quality stays `too_blurry` / `face_too_small` / etc., fix lighting/distance — do **not** lower quality thresholds.

## D. Known recognition

- [ ] Keep enrolled face in view on `/camera`
- [ ] Recognition shows known person name
- [ ] `Similarity: 0.xxx` with score ≥ threshold
- [ ] Not shown as a percentage

## E. Recognized event

- [ ] `/events` shows `recognized` for Test Person A
- [ ] Correct `person_id` / name association
- [ ] Reasonable timestamp

## F. Recognized cooldown

- [ ] Keep same person visible
- [ ] Events are **not** created on every frame
- [ ] After cooldown (~10s default), a new recognized event **may** appear

## G. Unknown person

- [ ] Show a face that was **not** enrolled
- [ ] Recognition = unknown
- [ ] `unknown_face` event created

## H. Unknown cooldown

- [ ] Keep unknown face visible
- [ ] No unknown event spam within cooldown

## I. Camera stop / restart

- [ ] Stop camera
- [ ] Preview stops; device released (other apps can open webcam)
- [ ] Start again; camera reopens

## J. Camera failure (optional)

- [ ] With camera running, unplug or disable webcam if safe
- [ ] App does not crash; error/stopped state visible
- [ ] Reconnect and restart camera (auto-reconnect is **not** required)

---

## Run log — 2026-08-16

| Field | Value |
| --- | --- |
| Date | 2026-08-16 (local evening, Asia/Tehran) |
| OS | Windows 11 (win32 10.0.26200) |
| Python | 3.13.1 |
| Node | v24.18.1 |
| Camera | USB Webcam (`CAMERA_DEVICE_INDEX=0`, backend `dshow`) |
| Resolution / FPS | 1280×720 @ ~15 FPS (driver-reported) |
| Recognition threshold | 0.363 |
| Cooldowns | recognized 10.0 s, unknown 10.0 s |
| Person under test | **Test Person A** `b1d9c5e7-290f-4139-bfec-3d498602da82` |
| Enrollment id | `49ccd9be-8877-4779-854e-803992dbcef7` |
| How exercised | Live USB webcam + REST API against running `npm run dev` (same backend the frontend uses) |

### Per-test results

| Test | Result | Observations |
| --- | --- | --- |
| A System startup | **PASS** | `GET /api/health` → `{"status":"ok"}`. `GET /api/system/status` → status ok, DB connected, camera available, threshold 0.363. Frontend `http://127.0.0.1:3000` → HTTP 200. Proxy `/backend/api/health` → ok. Note: DB was missing enrollment/events tables until `npm run db:migrate` (0002 + 0003) was applied during this run. |
| B Person creation | **PASS** | Created **Test Person A** via `POST /api/persons`. id=`b1d9c5e7-290f-4139-bfec-3d498602da82`, active=true, enrollment_count started at 0. |
| C Face enrollment | **PASS** | Camera started (`running`, 1280×720). Enrollment session reached `ready` (track_id=1, sharpness≈83.8→109.2, brightness≈87.9→107.7, face ~186–197 px). Capture → `completed`, enrollment_id=`49ccd9be-…`, person enrollment_count=1. Embedding dim=128 normalized. First session attempt failed with `camera_not_running` before start — not a quality rejection. |
| D Known recognition | **PASS** | Track recognition `status=matched`, `person_id` matches Test Person A, `person_display_name=Test Person A`. Live similarity samples include **0.8176981405790338**, **0.6313041261492603**, **0.785069167590127**, **0.5754521397966558** (all ≥ 0.363). |
| E Recognized event | **PASS** | Events include `event_type=recognized`, `person_id=b1d9c5e7-…`, `camera_id=default`, `track_id=1`, non-null `similarity` and `occurred_at` (e.g. sim **0.8941774643277176** at `2026-08-16T17:33:24.599592Z`). |
| F Recognized cooldown | **PASS** | Recognized events spaced ≈10 s apart (e.g. 17:33:24 → 17:33:34 → 17:33:44 → 17:33:54 → 17:34:04 → 17:34:14). Not emitted every frame while continuously matched. New event appears after cooldown. |
| G Unknown recognition | **BLOCKED** | **Phone photo — NOT a liveness test.** 60 s diagnostic (2026-08-16 ~22:31): **181/190** samples `too_blurry` (sharpness ~25–56; gate 60). **0** `unknown` samples. Category: **`PHOTO_QUALITY_BLOCKED`**. Brief early `matched` Test Person A (5 samples, sim ~0.42–0.45) not used as false-positive proof of the photo. |
| H Unknown event | **BLOCKED** | Not run in diagnostic (events/cooldown out of scope for this run); still blocked on G. |
| I Unknown cooldown | **BLOCKED** | Not run in diagnostic; still blocked on G. |
| J Camera stop/restart | **PASS** | Stop → state `closed`, `camera.running=false`. Start → `running` 1280×720. Pipeline resumed; after brief quality settle, recognition matched Test Person A again (sim **0.5754521397966558**). |
| K Camera failure (optional) | **NOT RUN** | Physical unplug not performed. |
| Liveness / anti-spoofing | **NOT TESTED** | Photo presentation is synthetic only; not claimed as liveness. |

### Diagnostic — phone photo unknown recognition (2026-08-16 ~22:31 local)

**Label:** phone photo presentation — **NOT** a liveness test.  
**Window:** 60 s observation. Threshold **0.363** unchanged. No code/config changes.

| Metric | Value |
| --- | --- |
| Samples | 190 |
| Quality accepted | 5 |
| Quality rejected | 181 |
| Reject reason | **`too_blurry`** (181) |
| Rejected sharpness | min **25.03**, max **55.89** (gate min_sharpness=**60**) |
| Accepted sharpness | min **61.90**, max **68.76** (only first ~1.5 s) |
| Recognition unknown | **0** |
| Matched Test Person A | 5 (only in that brief accepted window; brightness ~161–163) |
| Phone-period brightness (blurry) | ~108–112 |

**Interpretation:** After the opening second, the displayed phone face remained **`too_blurry`** and never produced `unknown` / `below_threshold`. The five early `matched` / Test Person A frames coincide with higher brightness and are **not** treated as proof of false-positive matching of the photo (likely live face still in frame at start).

**Diagnostic category: `PHOTO_QUALITY_BLOCKED`**

Phase 10.5 remains **PARTIAL** (not claimed PASS).

### How to finish G–I with a phone photo (operator)

1. **Test Person A completely out of camera view** (no reflection / second face).
2. Phone: max brightness, high-res still, face large, pin steady, reduce glare/moiré until sharpness ≥ **60** (UI not `too_blurry`).
3. Hold **≥30 s** with recognition staying **`unknown`** / `below_threshold` (no flicker to Test Person A).
4. Confirm `unknown_face` event (`person_id` null), then verify **10 s** unknown cooldown (no spam; second event after cooldown).
5. Record values here; set G–I to **PASS** only if observed. Still label: photo presentation — **NOT** liveness.

### Observed similarity (actual values only)

| Context | Similarity |
| --- | --- |
| Live match (post-enroll) | 0.8176981405790338 |
| Live match (cooldown window) | 0.6313041261492603 |
| Live match (post-cooldown wait) | 0.785069167590127 |
| Live match (after camera restart) | 0.5754521397966558 |
| Recognized events (samples) | 0.8941774643277176, 0.8446215201064916, 0.8000287580571189, 0.6349936122779852, 0.6051343384275331, 0.7408722362136462 |
| Brief below_threshold (attempt 2; not accepted as different-person proof) | 0.1226280648290446, 0.19783689108330726, 0.1557364782835748, 0.21753016974159117, 0.348908042359757 |

All listed **known/matched** scores are ≥ threshold **0.363**. Similarity is reported as a score, not a percentage.

### Quality rejections

| When | Reason |
| --- | --- |
| Successful enrollment path | None — session went to `ready` then `completed`. |
| Before camera start | Enrollment session `failed` / `error_code=camera_not_running` (operational, not quality). |
| Immediately after camera restart | Transient `quality_rejected` (recognition skipped) then recovered to accepted/matched within a few seconds. Exact quality reason codes were not captured on that transient sample. |

### Overall hardware verdict for this run

**PARTIAL** — A–F and camera stop/restart **PASS**; unknown path (G–I) **BLOCKED**. Latest diagnostic category: **`PHOTO_QUALITY_BLOCKED`** (phone photo fails sharpness gate). **Liveness: NOT TESTED.** Phase 10.5 **not** claimed PASS.

Use: **PASS** / **FAIL** / **BLOCKED** / **NOT RUN** only.

Do not mark overall Hardware E2E / Phase 10.5 **PASS** unless C–I (including unknown path) are **PASS**.
