#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 2 ]]; then
  echo "Usage: $0 <eks-base-url> <gke-base-url>" >&2
  exit 1
fi

check_target() {
  local base_url="$1"
  local session_id="verify-$(date +%s)"
  echo "[verify] ${base_url}"
  curl -fsS "${base_url%/}/health"
  curl -fsS -X POST "${base_url%/}/chat" \
    -H "Content-Type: application/json" \
    -d "{\"message\":\"hello from benchmark verifier\",\"session_id\":\"${session_id}\"}" >/dev/null
  history_json="$(curl -fsS "${base_url%/}/history/${session_id}")"
  if [[ "${history_json}" != *"\"message_count\":"* ]]; then
    echo "[verify] missing history payload at ${base_url}" >&2
    exit 1
  fi
}

check_target "$1"
check_target "$2"

echo "[verify] both endpoints healthy with redis-backed history path"
