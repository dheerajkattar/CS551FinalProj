# LLM FAQ Bot Deployment Contract (AWS EC2 + GKE)

This document defines runtime parity requirements for deploying `Applications/LLM_APP` on AWS EC2 and GCP GKE.

## 1) Runtime contract

- App type: ASGI (`FastAPI` app exposed by `main:app`).
- Container port: `5003`.
- Startup command:
  - `uvicorn main:app --host 0.0.0.0 --port ${PORT:-5003} --workers ${UVICORN_WORKERS:-2}`
- Runtime topology:
  - EC2 path: systemd-managed VM service.
  - GKE path: Deployment with HPA for autoscaling.

## 2) Required environment variables

- Required:
  - `GEMINI_API_KEY`
  - `REDIS_URL` (managed Redis endpoint per cloud)
- Recommended parity knobs:
  - `GEMINI_MODEL`
  - `GEMINI_REQUEST_TIMEOUT_SECONDS`
  - `RATE_LIMIT_RPM`
  - `CHAT_CONTEXT_MESSAGES`
  - `REDIS_KEY_PREFIX`
  - `REDIS_TIMEOUT_SECONDS`
  - `REDIS_SESSION_TTL_SECONDS`
  - `UVICORN_WORKERS`
  - `PORT`
  - `LOG_LEVEL`

## 3) Image/version contract

- Every benchmark run must use immutable app identifiers:
  - EC2: deployed git SHA/release ID.
  - GKE: immutable image tag (prefer git SHA).
- Store both identifiers in benchmark notes for reproducibility.

## 4) Platform resource contract

- AWS EC2:
  - VM host with systemd unit `llm-faq-bot.service`.
  - Security group exposes `22` and app port (`5003`) per benchmark policy.
  - Runtime `.env` at `Applications/LLM_APP/.env`.
- GKE:
  - Namespace, ServiceAccount, Deployment, Service, HPA, PodDisruptionBudget, Ingress.
  - Kubernetes `Secret` named `llm-api-secrets` with `GEMINI_API_KEY`, `REDIS_URL`.

## 5) Health/readiness contract

- `GET /health` must expose:
  - Gemini readiness (`key present`, model init state),
  - Redis readiness (`redis_configured`, `redis_ready`),
  - overall `ready` flag.
- GKE pod readiness probe uses `/health`.
- Degraded readiness if either Gemini config or Redis availability fails.

## 6) Stateful session contract

- `/chat` and `/history` use Redis-backed session storage on both platforms.
- Session keys are prefixed with `REDIS_KEY_PREFIX`.
- Session records carry TTL from `REDIS_SESSION_TTL_SECONDS`.
- Session behavior must remain stable across pod restarts and scale-out.

## 7) Networking contract

- Public endpoint via EC2 public IP / managed LB for AWS.
- Public endpoint via GKE ingress for GCP.
- Inbound access scoped to benchmark CIDRs where possible.
- Outbound HTTPS required for Gemini API traffic.
- Redis access restricted to host/network policy as applicable.

## 8) Logging and observability contract

- App logs include method/path/status/latency.
- No secret values in logs.
- Collect baseline metrics:
  - ingress latency + 4xx/5xx,
  - pod CPU/memory/restarts,
  - Redis connection and saturation metrics.

## 9) Rollback contract

- Roll back by immutable version reference + unchanged config/secrets references.
- Verify rollback success via:
  - service status (`systemctl`) on EC2 and rollout status on GKE,
  - `/health`,
  - `POST /chat` followed by `GET /history/{session_id}`.
