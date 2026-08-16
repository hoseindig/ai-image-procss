# Frontend (Phase 9)

Phase 9 adds a Next.js UI for testing the existing face recognition backend.

## Stack

- Next.js 15 (App Router) + TypeScript
- Tailwind CSS v4
- shadcn/ui primitives (Radix)
- TanStack Query

**Tested:** Windows 11, Node.js v24.18.1, npm 11.x  
**Documented:** Ubuntu LTS with Node 24+  
**Not hardware-tested in this phase:** Linux webcam + MJPEG end-to-end on Ubuntu

## Architecture

```text
USB Webcam
  → Backend (OpenCV capture + YuNet/SFace pipeline)
  → MJPEG GET /api/cameras/{id}/preview
  → Browser <img>

REST metadata (cameras, detections, persons, events, system)
  → Next.js same-origin rewrite /backend/* → FastAPI :8000
  → TanStack Query hooks
  → Pages
```

The browser does **not** call `getUserMedia()` for the main camera pipeline.
The browser does **not** run SFace or generate embeddings.

## Project layout

```text
frontend/src/
  app/                 # routes: /, /camera, /people, /people/[id], /events
  components/          # shell, states, shadcn/ui
  features/
    camera/
    people/
    events/
    system/
  lib/api/             # typed client
  lib/query/           # QueryClient + keys
  hooks/               # (shared hooks if needed)
  types/               # API types (no raw embeddings)
```

## API configuration

| Variable | Scope | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | Browser | Base path/URL for REST + MJPEG. Default `/backend` |
| `API_PROXY_TARGET` | Next server | Rewrite target. Default `http://127.0.0.1:8000` |

**Chosen approach:** same-origin proxy via Next.js rewrites (`/backend/:path*` → FastAPI). This avoids day-to-day CORS friction. Backend `CORS_ORIGINS` still lists `http://localhost:3000` and `http://127.0.0.1:3000` for direct access if you set `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`.

Do not put secrets in `NEXT_PUBLIC_*`.

## Pages

| Route | Role |
| --- | --- |
| `/` | Dashboard: health, system status, camera state, recent events |
| `/camera` | Start/stop, MJPEG preview, detection/recognition metadata |
| `/people` | List/create persons, activate/deactivate |
| `/people/[id]` | Detail, enrollment metadata, **developer** embedding paste |
| `/events` | Filters + backend pagination |

Similarity is shown as a score (`0.742`), never as a percentage.

## Enrollment UI note

Phase 7A enrollment POST still requires a precomputed 128-D vector. The person detail page exposes a clearly labeled **Developer / testing enrollment** panel. It does not claim to capture or embed faces in the browser. Future phases can enroll from the live camera pipeline.

## RTL

`html` uses `lang="fa"` and `dir="rtl"`. Spacing utilities prefer logical properties (`ps`/`pe`/`start`) where custom. Vazirmatn is the primary font.

## Scripts

From `frontend/`:

```powershell
npm install
npm run dev
npm run lint
npm run typecheck
npm run test
npm run build
npm run test:e2e:install
npm run test:e2e
```

Playwright smoke tests live in `frontend/e2e/`. They stub `/backend` responses and do not need a webcam. Browser binaries must be installed once (`npm run test:e2e:install`). If the Playwright CDN is unreachable, document the failure and rely on Vitest until install succeeds.

## Security

- Raw embeddings are never shown, stored in `localStorage`, or logged by the frontend.
- MJPEG and REST stay on the local backend / proxy.
- No third-party analytics.

## Non-goals (this phase)

- Plate detection / OCR / vehicles
- WebSockets / SSE
- Browser-side AI
- Video recording / snapshots
- Drawing detection boxes over MJPEG (unless backend provides an overlay stream)
