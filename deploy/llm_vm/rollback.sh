#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/llm-faq-bot}"
SERVICE_NAME="${SERVICE_NAME:-llm-faq-bot}"
TARGET_REF="${1:-}"

if [[ -z "${TARGET_REF}" ]]; then
  echo "Usage: $0 <git-ref>" >&2
  exit 1
fi

cd "${APP_DIR}"
git fetch --all --prune
git checkout "${TARGET_REF}"

if [[ -f "Applications/LLM_APP/requirements.txt" ]]; then
  .venv/bin/pip install -r Applications/LLM_APP/requirements.txt
fi

systemctl daemon-reload
systemctl restart "${SERVICE_NAME}"
systemctl --no-pager --full status "${SERVICE_NAME}" || true

echo "[rollback] rolled back to ${TARGET_REF}"
