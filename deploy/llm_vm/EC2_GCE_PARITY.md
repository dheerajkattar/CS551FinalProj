# EC2 + GCE VM Parity Guidance

Use this baseline to keep both deployments comparable for later benchmarks.

## Suggested parity profile

- OS image: Ubuntu 22.04 LTS (both clouds)
- vCPU/RAM target:
  - AWS EC2: `t3.small` (2 vCPU, 2 GiB)
  - GCP GCE: `e2-standard-2` (2 vCPU, 8 GiB) or `e2-medium` (2 vCPU, 4 GiB)
- Disk: 20 GB standard persistent disk
- Region strategy:
  - keep both in geographically similar regions (example: `us-east-1` and `us-east1`)
- Runtime settings:
  - `UVICORN_WORKERS=2`
  - `GEMINI_REQUEST_TIMEOUT_SECONDS=20`
  - `RATE_LIMIT_RPM=30`

## Network policy parity

- Open inbound:
  - `22/tcp` only from admin CIDR
  - `5003/tcp` only from benchmark client CIDR
- Allow outbound HTTPS for Gemini API traffic.

## Validation checklist

1. `systemctl status llm-faq-bot` is active on both VMs
2. `/health` returns `ready=true` on both VMs
3. `POST /ask` returns `200` on both VMs
4. same git ref deployed on both VMs
