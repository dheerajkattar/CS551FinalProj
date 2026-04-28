# LLM FAQ Bot Deployment Contract (EC2 + GCE)

This document defines the runtime contract for deploying `Applications/LLM_APP` on one AWS EC2 VM and one GCP Compute Engine VM.

## 1) Runtime and process contract

- Application type: ASGI (`FastAPI` app at `main:app`).
- Default port: `5003` (`PORT` environment variable can override).
- Recommended process command:
  - `uvicorn main:app --host 0.0.0.0 --port ${PORT:-5003} --workers ${UVICORN_WORKERS:-2}`
- Process manager: `systemd` (required for restart behavior).

## 2) Required environment variables

- Required:
  - `GEMINI_API_KEY`: Gemini API key for upstream model access.
- Optional runtime tuning:
  - `GEMINI_MODEL` (default: `gemini-1.5-flash-latest`)
  - `GEMINI_REQUEST_TIMEOUT_SECONDS` (default: `20`)
  - `RATE_LIMIT_RPM` (default: `30`, set `0` to disable)
  - `CHAT_CONTEXT_MESSAGES` (default: `5`)
  - `LOG_LEVEL` (default: `INFO`)
  - `UVICORN_WORKERS` (default: `2`)
  - `PORT` (default: `5003`)

## 3) `.env` file contract

- `.env` is the source for VM configuration and must not be committed.
- Recommended location: `/opt/llm-faq-bot/.env`.
- Required file permissions:
  - owner: service user (or root with controlled access)
  - mode: `600`
- Minimum required keys:
  - `GEMINI_API_KEY=<secret>`
- Optional keys may be added for tuning from section 2.

## 4) Networking contract

- Inbound:
  - Allow TCP `5003` from approved client CIDR ranges.
  - Restrict SSH (`22`) to administrative IPs only.
- Outbound:
  - Allow HTTPS egress for Gemini API calls.

## 5) Health and readiness contract

- Liveness endpoint: `GET /health`
  - `status = healthy` and `ready = true` when `GEMINI_API_KEY` is set.
  - `status = degraded` and `ready = false` when key is absent.
- Functional readiness check:
  - `POST /ask` with a lightweight prompt should return `200`.
  - Missing key must return `503` with non-secret error detail.

## 6) Logging contract

- Logs must include:
  - request method, path, HTTP status code, latency milliseconds.
- Logs must not include:
  - `GEMINI_API_KEY` or any sensitive header/body content.
- Preferred sink:
  - `journald` via `systemd`.

## 7) Startup and restart behavior

- Service must start via `systemd` unit with `EnvironmentFile=/opt/llm-faq-bot/.env`.
- Service restart policy:
  - `Restart=always`
  - `RestartSec=5`
- On startup without key:
  - service can remain up for observability, but `/ask` and `/chat` must return `503`.

## 8) Rollback contract

- Rollback unit of change:
  - previous Git revision + previous `.env` + same `systemd` unit.
- Rollback steps:
  1. stop service
  2. checkout previous revision
  3. reinstall dependencies if changed
  4. restore previous `.env`
  5. daemon-reload + restart
  6. validate `/health` and `POST /ask`
