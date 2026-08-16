# Acceptance Test (Phase 10.5)

Manual **Hardware E2E** acceptance checklist for the integrated face-recognition system.

This is **not** the Playwright browser suite. Playwright uses a mocked backend and does **not** prove webcam recognition.

| Suite | Webcam | AI | Purpose |
| --- | --- | --- | --- |
| Automated (`npm run test:all`) | No | Fake/unit | Regressions |
| Browser E2E (Playwright) | No | Mocked API | UI wiring |
| **This document** | **Yes** | **Real pipeline** | Acceptance |

**Threshold:** `FACE_RECOGNITION_THRESHOLD=0.363` (do not change). Show similarity as `0.xxx`, never as a percentage.

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

- [ ] Create person **Test Person**
- [ ] Person appears in `/people`

## C. Enrollment (real webcam)

- [ ] Open Test Person → **Enroll Face**
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

- [ ] `/events` shows `recognized` for Test Person
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

## Recording results

| Section | Result | Notes |
| --- | --- | --- |
| A System | | |
| B Person | | |
| C Enrollment | | |
| D Known | | |
| E Event | | |
| F Cooldown known | | |
| G Unknown | | |
| H Cooldown unknown | | |
| I Stop/restart | | |
| J Failure | | |

Use: **PASS** / **FAIL** / **NOT RUN**.

Do not mark overall Hardware E2E PASS unless C–I are PASS.
