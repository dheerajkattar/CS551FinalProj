#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${EC2_HOST:-}" || -z "${GCE_HOST:-}" || -z "${SSH_USER:-}" || -z "${SSH_KEY_PATH:-}" ]]; then
  cat <<'USAGE' >&2
Set required environment variables:
  EC2_HOST=<ip-or-dns>
  GCE_HOST=<ip-or-dns>
  SSH_USER=<ssh user>
  SSH_KEY_PATH=<path to private key>
Optional:
  REMOTE_APP_DIR=/opt/llm-faq-bot
  REPO_URL=<git url>
  REPO_REF=main
USAGE
  exit 1
fi

REMOTE_APP_DIR="${REMOTE_APP_DIR:-/opt/llm-faq-bot}"
REPO_REF="${REPO_REF:-main}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

sync_and_bootstrap() {
  local cloud_name="$1"
  local host="$2"
  local wrapper_script="$3"

  echo "[deploy:${cloud_name}] syncing repo to ${host}"
  rsync -az --delete \
    -e "ssh -i ${SSH_KEY_PATH}" \
    "${ROOT_DIR}/" "${SSH_USER}@${host}:${REMOTE_APP_DIR}/"

  echo "[deploy:${cloud_name}] running bootstrap wrapper"
  ssh -i "${SSH_KEY_PATH}" "${SSH_USER}@${host}" \
    "sudo REPO_REF='${REPO_REF}' REPO_URL='${REPO_URL:-}' APP_DIR='${REMOTE_APP_DIR}' bash '${REMOTE_APP_DIR}/${wrapper_script}'"

  echo "[deploy:${cloud_name}] done"
}

sync_and_bootstrap "ec2" "${EC2_HOST}" "deploy/llm_vm/cloud/ec2_setup.sh" &
pid_ec2=$!
sync_and_bootstrap "gce" "${GCE_HOST}" "deploy/llm_vm/cloud/gce_setup.sh" &
pid_gce=$!

wait "${pid_ec2}"
wait "${pid_gce}"

echo "[deploy] both targets completed bootstrap"
echo "[deploy] run verification:"
echo "  ${REMOTE_APP_DIR}/deploy/llm_vm/verify.sh http://${EC2_HOST}:5003 http://${GCE_HOST}:5003"
