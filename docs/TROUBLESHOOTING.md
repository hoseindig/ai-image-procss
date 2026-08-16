# Troubleshooting

## Backend will not start

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Validation error on settings | Bad env values | Check ranges in `.env.example`; invalid values are not clamped |
| Model path error | Missing ONNX files | `python scripts/download_models.py` (or `python3` on Linux) |
| Port in use | Stale process on 8000 | Stop the old process; restart `npm run dev` |
| Production reject DEBUG | `APP_ENV=production` with `DEBUG=true` | Set `DEBUG=false` |

## Frontend cannot reach backend

1. Confirm backend responds: `GET http://127.0.0.1:8000/api/health`
2. Confirm readiness: `GET http://127.0.0.1:8000/api/ready`
3. Check `CORS_ORIGINS` includes the frontend origin
4. Ensure Next.js proxies `/backend` (see `docs/FRONTEND.md`)

UI label: **Backend unavailable** when camera list fails with network error.

## Camera permissions / conflicts

| Issue | Guidance |
| --- | --- |
| Device busy | Close Zoom/Teams/other apps using the webcam |
| Wrong index | Set `CAMERA_DEVICE_INDEX` |
| Windows backend | Try `CAMERA_BACKEND=dshow` then `msmf` |
| Linux permissions | Ensure user can access `/dev/video*`; group `video` often required |
| State ERROR | Click Start again (`CAMERA_RECOVER_ON_START`); or Stop then Start |

## Model / ONNX errors

- Missing file → fail-fast at settings (non-test) or at factory load
- Corrupt ONNX → `ModelLoadError` / clear API/log message
- Provider is CPU only (no GPU path in this project)

## Database errors

- Ensure `npm run db:migrate` (Alembic) before first run
- Relative SQLite paths resolve from project root
- Locking: single-writer SQLite; avoid multiple app instances on the same file DB
- Event write failures are logged; recognition continues (cooldown slot rolled back)

## Recognition / quality

| UI / status | Meaning |
| --- | --- |
| No face | No detection in latest processed frame |
| Quality rejected | Sharpness/size/brightness gate (`FACE_QUALITY_MIN_SHARPNESS=60` default) |
| Unknown face | Below cosine threshold `0.363` |
| Known person | Matched gallery sample |
| Recognition unavailable | Detection API error or feature disabled |

Phone photos of faces often fail sharpness (**PHOTO_QUALITY_BLOCKED** in acceptance notes).

## Playwright

Chromium download failures (`ECONNRESET`, CDN): mark Browser E2E **BLOCKED**. Unit/API tests remain valid.

## Logging

Do not expect an INFO line per recognition frame. Use `LOG_LEVEL=DEBUG` for match/unknown/track churn.

Never expect embeddings or image bytes in logs.
