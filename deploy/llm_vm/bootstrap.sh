#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/llm-faq-bot}"
APP_SUBDIR="${APP_SUBDIR:-Applications/LLM_APP}"
SERVICE_USER="${SERVICE_USER:-llmapp}"
SERVICE_NAME="${SERVICE_NAME:-llm-faq-bot}"
REPO_URL="${REPO_URL:-}"
REPO_REF="${REPO_REF:-main}"
SKIP_GIT_SYNC="${SKIP_GIT_SYNC:-}"
ENV_SOURCE_FILE="${ENV_SOURCE_FILE:-}"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-${APP_SUBDIR}/requirements.txt}"
SYSTEMD_TEMPLATE="${SYSTEMD_TEMPLATE:-deploy/llm_vm/systemd/llm-faq-bot.service}"
APP_WORKDIR="${APP_DIR}/${APP_SUBDIR}"
ENV_FILE_PATH="${APP_WORKDIR}/.env"

echo "[bootstrap] app_dir=${APP_DIR} app_subdir=${APP_SUBDIR} service_user=${SERVICE_USER} service_name=${SERVICE_NAME} repo_ref=${REPO_REF}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this script as root (or with sudo)." >&2
  exit 1
fi

if command -v apt-get >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y git python3 python3-venv python3-pip curl
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y git python3 python3-pip
elif command -v yum >/dev/null 2>&1; then
  yum install -y git python3 python3-pip
else
  echo "Unsupported package manager. Install git/python3/pip manually." >&2
  exit 1
fi

id -u "${SERVICE_USER}" >/dev/null 2>&1 || useradd --system --create-home --shell /bin/bash "${SERVICE_USER}"
mkdir -p "${APP_DIR}"

if [[ -n "${REPO_URL}" && ! -d "${APP_DIR}/.git" ]]; then
  rm -rf "${APP_DIR:?}"/*
  git clone "${REPO_URL}" "${APP_DIR}"
fi

if [[ ! -d "${APP_DIR}/.git" ]]; then
  echo "Expected git repository at ${APP_DIR}. Either set REPO_URL or pre-stage code." >&2
  exit 1
fi

if [[ -z "${SKIP_GIT_SYNC}" && -z "${REPO_URL}" ]]; then
  SKIP_GIT_SYNC="true"
fi

if [[ "${SKIP_GIT_SYNC}" == "true" ]]; then
  echo "[bootstrap] skipping git fetch/checkout/pull (pre-staged code)"
else
  cd "${APP_DIR}"
  git fetch --all --prune
  git checkout "${REPO_REF}"
  git pull --ff-only
fi

if [[ ! -d "${APP_WORKDIR}" ]]; then
  echo "App subdirectory ${APP_WORKDIR} not found." >&2
  exit 1
fi

cd "${APP_WORKDIR}"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r "${APP_DIR}/${REQUIREMENTS_FILE}"

if [[ -n "${ENV_SOURCE_FILE}" ]]; then
  cp "${ENV_SOURCE_FILE}" "${ENV_FILE_PATH}"
fi

if [[ ! -f "${ENV_FILE_PATH}" ]]; then
  echo "Missing ${ENV_FILE_PATH}. Create it from Applications/LLM_APP/.env.example." >&2
  exit 1
fi

if ! grep -q '^GEMINI_API_KEY=' "${ENV_FILE_PATH}"; then
  echo "GEMINI_API_KEY is missing in ${ENV_FILE_PATH}." >&2
  exit 1
fi

chown "${SERVICE_USER}:${SERVICE_USER}" "${ENV_FILE_PATH}"
chmod 600 "${ENV_FILE_PATH}"
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${APP_DIR}"

rendered_unit="/etc/systemd/system/${SERVICE_NAME}.service"
sed \
  -e "s|__APP_DIR__|${APP_DIR}|g" \
  -e "s|__APP_WORKDIR__|${APP_WORKDIR}|g" \
  -e "s|__SERVICE_USER__|${SERVICE_USER}|g" \
  "${APP_DIR}/${SYSTEMD_TEMPLATE}" > "${rendered_unit}"

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl restart "${SERVICE_NAME}"
systemctl --no-pager --full status "${SERVICE_NAME}" || true

echo "[bootstrap] completed. verify with: curl -fsS http://localhost:\${PORT:-5003}/health"
