#!/usr/bin/env bash
set -euo pipefail

OUT_FILE="${1:-llm_runtime_config.json}"
NAMESPACE="${NAMESPACE:-llm-bench}"

kubectl -n "${NAMESPACE}" get configmap llm-api-config -o json > "${OUT_FILE}"
kubectl -n "${NAMESPACE}" get deployment llm-api -o json >> "${OUT_FILE}"

echo "[config] exported runtime config to ${OUT_FILE}"
