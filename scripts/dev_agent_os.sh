#!/usr/bin/env bash
# Start Agno AgentOS (backend) and the Vue chat frontend for local development.
#
# The Vite dev server proxies browser requests from /agent-os to the AgentOS
# process (see src/frontend/vite.config.js). Set VITE_AGENT_OS_ORIGIN if your
# backend listens elsewhere.
#
# Prereqs: Postgres via KMA_DB_* (or legacy DB_*) in .env (e.g. ./scripts/starter.sh for agent-db + Ollama),
#          `uv sync`, and in src/frontend: `npm ci` (or npm install).
#
# From repo root:
#   ./scripts/dev_agent_os.sh
#
# Backend only (same as before):
#   KMA_SKIP_FRONTEND=1 ./scripts/dev_agent_os.sh
#   SKIP_FRONTEND=1 ./scripts/dev_agent_os.sh
#
# Optional environment (prefer KMA_*; legacy names in parentheses):
#   KMA_AGENT_OS_HOST (AGENT_OS_HOST)  Bind address for AgentOS (default: 127.0.0.1)
#   KMA_AGENT_OS_PORT (AGENT_OS_PORT, PORT)  AgentOS port (default: 8000)
#   KMA_VITE_PORT (VITE_PORT)      Vite dev port (default: 5174; read from src/frontend/.env if set)
#   RUNTIME_ENV    e.g. dev
#   AGNO_DEBUG     e.g. True
#   KMA_SKIP_FRONTEND (SKIP_FRONTEND)  Set to 1 to run only AgentOS in the foreground (no Vite)

set -euo pipefail

die() {
  echo "dev_agent_os.sh: $*" >&2
  exit 1
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}" || die "cannot cd to ${REPO_ROOT}"

export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
export AGENT_OS_HOST="${KMA_AGENT_OS_HOST:-${AGENT_OS_HOST:-127.0.0.1}}"
export AGENT_OS_PORT="${KMA_AGENT_OS_PORT:-${AGENT_OS_PORT:-${PORT:-8000}}}"
export RUNTIME_ENV="${RUNTIME_ENV:-dev}"
export AGNO_DEBUG="${AGNO_DEBUG:-True}"

FRONTEND_DIR="${REPO_ROOT}/src/frontend"

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

have_cmd uv || die "uv not found; install uv and run 'uv sync' from the repo root."

if [[ "${KMA_SKIP_FRONTEND:-${SKIP_FRONTEND:-0}}" == "1" ]]; then
  if [[ -f "${REPO_ROOT}/.env" ]]; then
    exec uv run --env-file "${REPO_ROOT}/.env" python -m app.main
  else
    exec uv run python -m app.main
  fi
fi

have_cmd npm || die "npm not found; install Node.js to run the frontend."

[[ -d "${FRONTEND_DIR}/node_modules" ]] ||
  die "frontend dependencies missing; run: (cd src/frontend && npm ci)"

BACKEND_PID=""
cleanup() {
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    echo "Stopping AgentOS (pid ${BACKEND_PID})..." >&2
    kill "${BACKEND_PID}" 2>/dev/null || true
    wait "${BACKEND_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if [[ -f "${REPO_ROOT}/.env" ]]; then
  uv run --env-file "${REPO_ROOT}/.env" python -m app.main &
else
  uv run python -m app.main &
fi
BACKEND_PID=$!

BACKEND_URL="http://127.0.0.1:${AGENT_OS_PORT}"
export VITE_AGENT_OS_ORIGIN="${VITE_AGENT_OS_ORIGIN:-${BACKEND_URL}}"

echo "AgentOS starting (${BACKEND_URL}, pid ${BACKEND_PID})..." >&2
echo "Vite will proxy /agent-os → ${VITE_AGENT_OS_ORIGIN}" >&2

if have_cmd curl; then
  ready=0
  for _ in $(seq 1 60); do
    if curl -sf "${BACKEND_URL}/agents" >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 0.5
  done
  if [[ "${ready}" -ne 1 ]]; then
    echo "dev_agent_os.sh: timed out waiting for GET ${BACKEND_URL}/agents; starting Vite anyway." >&2
  fi
else
  sleep 2
fi

cd "${FRONTEND_DIR}" || die "cannot cd to ${FRONTEND_DIR}"
npm run dev
