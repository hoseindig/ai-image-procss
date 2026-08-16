# Security (Phase 11)

Local-first face camera system. Localhost does **not** make every security concern irrelevant.

## Security model

| Assumption | Detail |
| --- | --- |
| Trust boundary | Operator-controlled machine; API bound to `127.0.0.1` by default |
| Biometrics | Engineering face matching, not certified authentication |
| Data at rest | SQLite: people, enrollments (embeddings), events (metadata only) |
| Data in transit | Same host HTTP; no TLS in default local setup |

## Explicit non-goals

- Multi-tenant SaaS hardening
- Public internet exposure
- Hardware security modules / encrypted-at-rest by default
- Liveness / anti-spoofing (not implemented)
- Fine-grained RBAC / authN

## Controls (current)

| Control | Status |
| --- | --- |
| `RECOGNITION_TEST_MODE` default **false**; production forbids enabling it | PASS |
| No raw embeddings in normal GET APIs | PASS |
| No embeddings / images in structured logs | PASS (policy + demoted chatty logs) |
| CORS: no wildcard `*` | PASS (validated) |
| FastAPI `debug=False` for HTTP (no stack traces to clients) | PASS |
| `DEBUG` JSON details only when settings.debug; forbidden in production | PASS |
| Model paths fail-fast when features enabled (non-test env) | PASS |
| Path traversal: enrollment/preview use app-controlled streams, not user path reads | PASS (review) |
| Test-only `POST /api/test/recognize` returns 403 when disabled | PASS |

## Operator guidance

1. Keep `HOST=127.0.0.1` unless you intentionally expose the LAN.
2. For any non-local bind, add network controls and prefer TLS termination elsewhere.
3. Do not commit `.env` or database files with real enrollments.
4. Never enable `RECOGNITION_TEST_MODE` for production webcam use.
5. Treat gallery embeddings as sensitive biometric-adjacent data.

## Secrets

No cloud API keys are required for the core pipeline. Do not place credentials in logs or commit them.

## Oversized / malformed images

Enrollment capture is server-side from the camera pipeline. External multipart test endpoints are gated by `RECOGNITION_TEST_MODE`. Malformed images should fail with stable error codes without leaking stack traces.
