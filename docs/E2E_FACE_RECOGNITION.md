# End-to-End Face Recognition Validation (Phase 10)

Validate the full local pipeline after camera enrollment.

```text
Camera → YuNet → Track → Quality → Align → SFace
  → Gallery recognition → Events (+ cooldown) → Frontend
```

**Threshold:** `FACE_RECOGNITION_THRESHOLD=0.363` (unchanged). Similarity is a score, not a probability or percentage.

## Prerequisites

- Backend + frontend running (see `docs/SETUP.md`)
- Models present (`docs/MODELS.md`)
- USB webcam (**TESTED** path: Windows 11)

## Manual checklist (hardware)

1. Create person (e.g. `Test Person`)
2. Open person details → **Enroll Face**
3. Ensure camera is running; show **exactly one** face
4. Wait until state is `ready` / Quality: OK
5. Capture → enrollment count increases
6. Stay in frame → Camera page shows matched person + `Similarity: 0.xxx`
7. Confirm `recognized` event for that `person_id`
8. Remain visible through cooldown (~10s) → no event spam
9. After cooldown, another recognized event may appear
10. Unregistered face → `unknown` recognition + `unknown_face` event
11. Same unknown track within cooldown → no second unknown event

Only report steps actually performed.

## Automated coverage

| Area | Coverage |
| --- | --- |
| Enrollment session lifecycle | `tests/test_enrollment_session.py` |
| Prior recognition / events | existing Phase 7B/8 suites |
| Frontend enrollment UI states | Vitest panel + message tests |

Playwright: install Chromium when CDN is available (`npm run test:e2e:install`). If blocked, document and rely on Vitest + manual checks.

## Labels

| Item | Status |
| --- | --- |
| Automated enrollment session tests | **TESTED** |
| Full webcam known/unknown/cooldown in this agent run | report honestly in Phase 10 final status |
| Linux hardware E2E | **DOCUMENTED**, **NOT HARDWARE-TESTED** |
