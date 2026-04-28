# LLM FAQ Bot (VM Deployment Track)

FastAPI service for single-turn and multi-turn Q&A using Gemini.  
Current primary deployment target is **one EC2 VM** and **one GCE VM** with equivalent runtime settings.

## API Endpoints

- `POST /ask` - Single-turn question answering.
- `POST /chat` - Multi-turn chat with per-session in-memory context.
- `GET /history/{session_id}` - Session conversation history.
- `DELETE /history/{session_id}` - Clear one session history.
- `GET /health` - Liveness + readiness (`ready=true` only when key is configured).

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
GEMINI_MODEL=gemini-1.5-flash-latest
GEMINI_REQUEST_TIMEOUT_SECONDS=20
RATE_LIMIT_RPM=30
CHAT_CONTEXT_MESSAGES=5
UVICORN_WORKERS=2
PORT=5003
LOG_LEVEL=INFO
```

## Simultaneous EC2 + GCE Deployment

Artifacts live in `deploy/llm_vm`.

### 1) Prepare each VM

- Ubuntu 22.04 or equivalent Linux.
- Open inbound:
  - `22/tcp` only from admin CIDR.
  - `5003/tcp` from benchmark client CIDR.
- Ensure outbound HTTPS is allowed.

### 2) Stage `.env` on each VM

Recommended path:

```bash
sudo mkdir -p /opt/llm-faq-bot
sudo cp .env /opt/llm-faq-bot/.env
sudo chmod 600 /opt/llm-faq-bot/.env
```

### 3) Run deployment wrapper on each VM (manual)

On EC2:

```bash
sudo APP_DIR=/opt/llm-faq-bot REPO_URL=<repo-url> REPO_REF=main bash /opt/llm-faq-bot/deploy/llm_vm/cloud/ec2_setup.sh
```

On GCE:

```bash
sudo APP_DIR=/opt/llm-faq-bot REPO_URL=<repo-url> REPO_REF=main bash /opt/llm-faq-bot/deploy/llm_vm/cloud/gce_setup.sh
```

### 4) Deploy both in parallel from your machine

```bash
EC2_HOST=<ec2-ip-or-dns> \
GCE_HOST=<gce-ip-or-dns> \
SSH_USER=<ssh-user> \
SSH_KEY_PATH=<private-key-path> \
REPO_REF=main \
bash deploy/llm_vm/deploy_parallel.sh
```

### 5) Verify both targets

```bash
bash deploy/llm_vm/verify.sh http://<ec2-host>:5003 http://<gce-host>:5003
```

## Operations Runbook

- Service status:
  - `sudo systemctl status llm-faq-bot`
- Restart:
  - `sudo systemctl restart llm-faq-bot`
- Logs:
  - `sudo journalctl -u llm-faq-bot -f`
- Rollback:
  - `sudo APP_DIR=/opt/llm-faq-bot bash /opt/llm-faq-bot/deploy/llm_vm/rollback.sh <git-ref>`

## Known Limitations

- Conversation history is in-memory and not shared across VMs.
- Rate limiting is in-memory per session ID (single-node guardrail, not global).
- Upstream Gemini latency and quotas dominate throughput behavior.

## Benchmark Input Checklist (for next phase)

Provide these fields before running cross-cloud matrix benchmarks:

- EC2 base URL and GCE base URL.
- Runtime parity values (`UVICORN_WORKERS`, timeout, rate-limit, model).
- Test ingress policy (public CIDR vs restricted client).
- Warmup policy (warmup duration or request count).
- Concurrency levels and total request budgets.
- Prompt set definition (short vs long prompts, chat-turn depth).

## Testing

From repository root:

```bash
pytest tests/llm -m "api or asyncmock"
```
