#!/usr/bin/env bash
set -euo pipefail

OVERLAY="${1:-}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_REPO="${IMAGE_REPO:-ghcr.io/example/cs551-llm}"

if [[ "${OVERLAY}" != "eks" && "${OVERLAY}" != "gke" ]]; then
  echo "Usage: $0 <eks|gke>" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OVERLAY_DIR="${SCRIPT_DIR}/../overlays/${OVERLAY}"

kubectl apply -f "${SCRIPT_DIR}/../base/secret.example.yaml"
kubectl apply -k "${OVERLAY_DIR}"
kubectl -n llm-bench set image deployment/llm-api llm-api="${IMAGE_REPO}:${IMAGE_TAG}"
kubectl -n llm-bench rollout status deployment/llm-api

echo "[deploy] ${OVERLAY} deployed with image ${IMAGE_REPO}:${IMAGE_TAG}"
