#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 1 ]]; then
  echo "Usage: $0 <base-url-1> [base-url-2 ...]" >&2
  exit 1
fi

for base_url in "$@"; do
  echo "[verify] ${base_url}"
  health="$(curl -fsS "${base_url%/}/health")"
  echo "${health}"

  if [[ "${health}" != *"\"ready\":true"* ]]; then
    echo "[verify] service not ready at ${base_url}" >&2
    exit 1
  fi

  ask_status="$(curl -sS -o /dev/null -w "%{http_code}" \
    -X POST "${base_url%/}/ask" \
    -H "Content-Type: application/json" \
    -d '{"question":"ping","session_id":"smoke"}')"
  if [[ "${ask_status}" != "200" ]]; then
    echo "[verify] /ask failed with HTTP ${ask_status} at ${base_url}" >&2
    exit 1
  fi
done

echo "[verify] all targets healthy and ready"
