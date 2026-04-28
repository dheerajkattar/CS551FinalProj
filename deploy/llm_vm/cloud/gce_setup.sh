#!/usr/bin/env bash
set -euo pipefail

echo "[gce] starting cloud-specific setup"

export APP_DIR="${APP_DIR:-/opt/llm-faq-bot}"
export SERVICE_USER="${SERVICE_USER:-llmapp}"
export SERVICE_NAME="${SERVICE_NAME:-llm-faq-bot}"

# GCE firewall should allow:
# - tcp/22 from admin IP ranges
# - tcp/5003 from test client ranges
# This script assumes those are configured from GCP side.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/../bootstrap.sh"

echo "[gce] setup complete"
