# EC2 + GKE Parity Guidance

Use this baseline to keep EC2 and GKE deployments comparable for later benchmarks.

## Suggested parity profile

- OS image: Ubuntu 22.04 LTS (both clouds)
- vCPU/RAM target:
  - AWS EC2: `t3.small` (2 vCPU, 2 GiB)
  - GCP GKE node pool: `e2-standard-2` (2 vCPU, 8 GiB) x 2 nodes
- Disk: 20 GB baseline node/instance disk
- Region strategy:
  - keep both in geographically similar regions (example: `us-east-1` and `us-east1`)
- Runtime settings:
  - `UVICORN_WORKERS=2`
  - `GEMINI_REQUEST_TIMEOUT_SECONDS=20`
  - `RATE_LIMIT_RPM=30`

## Network and ingress parity

- Open inbound:
  - `22/tcp` only from admin CIDR
  - `5003/tcp` only from benchmark client CIDR
- Allow outbound HTTPS for Gemini API traffic.
- GKE ingress should be in namespace `llm-bench`.

## Validation checklist

1. `systemctl status llm-faq-bot` is active on EC2
2. `kubectl -n llm-bench rollout status deploy/llm-api` succeeds on GKE
3. `/health` returns `ready=true` on both endpoints
4. `POST /ask` returns `200` on both endpoints
5. both sides use aligned runtime env values + Redis parity knobs
