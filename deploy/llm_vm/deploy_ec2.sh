#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${EC2_HOST:-}" || -z "${SSH_KEY_PATH:-}" ]]; then
  echo "Usage: EC2_HOST=<public-ip> SSH_KEY_PATH=<path.pem> [GEMINI_API_KEY=...] $0" >&2
  exit 1
fi

APP_DIR="${APP_DIR:-/opt/llm-faq-bot}"
SSH_USER="${SSH_USER:-ec2-user}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-2.5-flash}"
REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
REDIS_KEY_PREFIX="${REDIS_KEY_PREFIX:-llm}"
REDIS_TIMEOUT_SECONDS="${REDIS_TIMEOUT_SECONDS:-2}"
REDIS_SESSION_TTL_SECONDS="${REDIS_SESSION_TTL_SECONDS:-86400}"

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  echo "GEMINI_API_KEY is required." >&2
  exit 1
fi

echo "[ec2] syncing repository to ${EC2_HOST}"
ssh -o StrictHostKeyChecking=no -i "${SSH_KEY_PATH}" "${SSH_USER}@${EC2_HOST}" \
  "sudo mkdir -p ${APP_DIR} && sudo chown -R ${SSH_USER}:${SSH_USER} ${APP_DIR}"
rsync -az --delete \
  -e "ssh -o StrictHostKeyChecking=no -i ${SSH_KEY_PATH}" \
  ./ "${SSH_USER}@${EC2_HOST}:${APP_DIR}/"

echo "[ec2] installing local redis service"
ssh -o StrictHostKeyChecking=no -i "${SSH_KEY_PATH}" "${SSH_USER}@${EC2_HOST}" \
  "sudo dnf install -y redis6 && sudo systemctl enable --now redis6"

echo "[ec2] writing runtime env"
ssh -o StrictHostKeyChecking=no -i "${SSH_KEY_PATH}" "${SSH_USER}@${EC2_HOST}" \
  "cat > ${APP_DIR}/Applications/LLM_APP/.env <<'EOF'
GEMINI_API_KEY=${GEMINI_API_KEY}
GEMINI_MODEL=${GEMINI_MODEL}
GEMINI_REQUEST_TIMEOUT_SECONDS=20
RATE_LIMIT_RPM=60
CHAT_CONTEXT_MESSAGES=5
UVICORN_WORKERS=2
PORT=5003
LOG_LEVEL=INFO
REDIS_URL=${REDIS_URL}
REDIS_KEY_PREFIX=${REDIS_KEY_PREFIX}
REDIS_TIMEOUT_SECONDS=${REDIS_TIMEOUT_SECONDS}
REDIS_SESSION_TTL_SECONDS=${REDIS_SESSION_TTL_SECONDS}
EOF"

echo "[ec2] bootstrapping systemd service"
ssh -o StrictHostKeyChecking=no -i "${SSH_KEY_PATH}" "${SSH_USER}@${EC2_HOST}" \
  "sudo APP_DIR=${APP_DIR} SERVICE_NAME=llm-faq-bot SERVICE_USER=llmapp SKIP_GIT_SYNC=true bash ${APP_DIR}/deploy/llm_vm/bootstrap.sh"

echo "[ec2] verifying endpoint"
curl -fsS "http://${EC2_HOST}:5003/health"
