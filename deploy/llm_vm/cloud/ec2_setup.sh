#!/usr/bin/env bash
set -euo pipefail

echo "[ec2] starting cloud-specific setup"

# EC2 defaults (Amazon Linux/Ubuntu are both supported by bootstrap script)
export APP_DIR="${APP_DIR:-/opt/llm-faq-bot}"
export SERVICE_USER="${SERVICE_USER:-llmapp}"
export SERVICE_NAME="${SERVICE_NAME:-llm-faq-bot}"

# Security group should allow:
# - tcp/22 from admin IP ranges
# - tcp/5003 from test client ranges
# This script assumes those are configured from AWS side.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/../bootstrap.sh"

echo "[ec2] setup complete"
