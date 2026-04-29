# LLM FAQ Bot (AWS EC2 + GCP GKE Deployment Track)

FastAPI service for single-turn and multi-turn Q&A using Gemini.  
Primary deployment target is now **EC2 (AWS)** and **GKE (GCP)** with Redis-backed session state on both platforms.

## API Endpoints

- `POST /ask` - Single-turn question answering.
- `POST /chat` - Multi-turn chat with per-session Redis-backed context.
- `GET /history/{session_id}` - Session conversation history.
- `DELETE /history/{session_id}` - Clear one session history.
- `GET /health` - Liveness + readiness (`ready=true` only when Gemini and Redis are healthy).

## Local Run

From `Applications/LLM_APP`:

```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 5003 --workers 2
```

Open `http://localhost:5003/docs`.

## Configuration (`.env`)

Required:

```bash
GEMINI_API_KEY=replace-with-your-key
```

Optional:

```bash
GEMINI_MODEL=gemini-2.5-flash
GEMINI_REQUEST_TIMEOUT_SECONDS=20
RATE_LIMIT_RPM=30
CHAT_CONTEXT_MESSAGES=5
UVICORN_WORKERS=2
PORT=5003
LOG_LEVEL=INFO
REDIS_URL=redis://managed-redis-endpoint:6379/0
REDIS_KEY_PREFIX=llm
REDIS_TIMEOUT_SECONDS=2
REDIS_SESSION_TTL_SECONDS=86400
```

## AWS EC2 + GKE Deployment

Artifacts live in:

- AWS EC2: `deploy/llm_vm`
- GKE: `deploy/llm_k8s`

### 1) Provision infrastructure

AWS EC2:

```bash
bash deploy/llm_vm/provision_ec2.sh
```

GKE + managed Redis:

```bash
PROJECT_ID=<gcp-project-id> bash deploy/llm_k8s/scripts/provision_gke.sh
```

### 2) Deploy AWS EC2 app runtime

Use EC2 public IP and key path from the provisioning step:

```bash
EC2_HOST=<ec2-public-ip> \
SSH_KEY_PATH=deploy/llm_vm/.keys/cs551-llm-ec2-key.pem \
GEMINI_API_KEY=<api-key> \
bash deploy/llm_vm/deploy_ec2.sh
```

### 3) Prepare GKE Kubernetes secret values

Update and apply:

```bash
kubectl apply -f deploy/llm_k8s/base/secret.example.yaml
```

### 4) Deploy GKE overlay

```bash
IMAGE_REPO=<registry/image> IMAGE_TAG=<git-sha> bash deploy/llm_k8s/scripts/deploy.sh gke
```

### 5) Verify EC2 + GKE endpoints

```bash
bash deploy/llm_vm/verify.sh http://<ec2-public-ip>:5003 http://<gke-ingress-ip>
```

## Operations Runbook

- EC2 service status:
  - `ssh -i <key.pem> ec2-user@<ec2-ip> 'sudo systemctl status llm-faq-bot --no-pager'`
- EC2 service logs:
  - `ssh -i <key.pem> ec2-user@<ec2-ip> 'sudo journalctl -u llm-faq-bot -n 100 --no-pager'`
- Rollout status:
  - `kubectl -n llm-bench rollout status deployment/llm-api`
- Pod logs:
  - `kubectl -n llm-bench logs deploy/llm-api --tail=100 -f`
- Scale:
  - `kubectl -n llm-bench scale deploy/llm-api --replicas=3`
- Export parity config:
  - `bash deploy/llm_k8s/scripts/export_runtime_config.sh llm_runtime_config.json`

## Known Limitations

- Redis dependency is required for shared chat history behavior.
- Rate limiting is in-memory per session ID (single-node guardrail, not global).
- Upstream Gemini latency and quotas dominate throughput behavior.

## Benchmark Input Checklist (for next phase)

Provide these fields before running cross-cloud matrix benchmarks:

- EC2 base URL and GKE ingress base URL.
- Runtime parity values (`UVICORN_WORKERS`, timeout, rate-limit, model).
- Redis endpoint strategy and session TTL settings.
- Test network policy (security groups + GKE ingress policy).
- Warmup policy (warmup duration or request count).
- Concurrency levels and total request budgets.
- Prompt set definition (short vs long prompts, chat-turn depth).

## Testing

From repository root:

```bash
pytest tests/llm -m "api or asyncmock"
```
