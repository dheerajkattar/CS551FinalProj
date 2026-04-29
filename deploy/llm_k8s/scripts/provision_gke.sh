#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:?Set PROJECT_ID}"
REGION="${REGION:-us-east1}"
ZONE="${ZONE:-us-east1-b}"
CLUSTER_NAME="${CLUSTER_NAME:-cs551-llm-gke}"
MACHINE_TYPE="${MACHINE_TYPE:-e2-standard-2}"
NODE_COUNT="${NODE_COUNT:-2}"
REDIS_NAME="${REDIS_NAME:-cs551-llm-redis}"
REDIS_SIZE_GB="${REDIS_SIZE_GB:-1}"
NETWORK="${NETWORK:-default}"

cat <<EOF
[gke] provisioning summary
  project: ${PROJECT_ID}
  cluster: ${CLUSTER_NAME}
  region/zone: ${REGION}/${ZONE}
  machine/count: ${MACHINE_TYPE} x ${NODE_COUNT}
  redis: ${REDIS_NAME} (${REDIS_SIZE_GB}GB)
EOF

gcloud config set project "${PROJECT_ID}"

gcloud container clusters create "${CLUSTER_NAME}" \
  --zone "${ZONE}" \
  --machine-type "${MACHINE_TYPE}" \
  --num-nodes "${NODE_COUNT}" \
  --release-channel regular

gcloud container clusters get-credentials "${CLUSTER_NAME}" --zone "${ZONE}" --project "${PROJECT_ID}"

gcloud redis instances create "${REDIS_NAME}" \
  --region "${REGION}" \
  --zone "${ZONE}" \
  --tier basic \
  --size "${REDIS_SIZE_GB}" \
  --redis-version redis_7_0 \
  --network "${NETWORK}"

echo "[gke] finished. ensure firewall allows benchmark CIDR to ingress LB."
