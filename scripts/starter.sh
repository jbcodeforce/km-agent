#!/usr/bin/env bash
# Start local stack: Postgres + km-agent (Docker by default), or Postgres + AgentOS via uv (--dev).
# OMLX stays on the host (not in Compose); this script can foreground `omlx serve` when needed.
#
# From the repository root:
#   ./scripts/starter.sh                    # docker compose up -d km-agent (and deps), then OMLX if needed
#   ./scripts/starter.sh --dev              # Postgres only + uv backend (stop Docker km-agent first if it uses :8000)
#   ./scripts/starter.sh --dev --frontend   # same as --dev, then Vite chat UI (backend in background)
#
# Options:
#   --dev        Run `uv sync` then AgentOS with `uv run` using `.venv`. Requires uv; OMLX must already respond.
#   --frontend   With --dev: start AgentOS in the background, wait for GET /agents, then `npm run dev`.
#   -h, --help
#
# Environment:
#   KMA_MLX_BASE_URL  OMLX OpenAI-compatible base URL (default: http://127.0.0.1:7999/v1).
#   OMLX_PORT         Host port for `omlx serve` when not already running (default: 7999).
#   OMLX_MODEL_DIR    Model directory for `omlx serve` (default: $HOME/.lmstudio/models).
#   KMA_AGENT_OS_HOST (AGENT_OS_HOST)  Bind address for AgentOS (default: 127.0.0.1)
#   KMA_AGENT_OS_PORT (AGENT_OS_PORT, PORT)  AgentOS port (default: 8000)
#   KMA_VITE_PORT (VITE_PORT)  Vite dev port (default: 5174; read from src/frontend/.env if set)
#   RUNTIME_ENV, AGNO_DEBUG  Passed through to AgentOS (defaults: dev, True)

set -euo pipefail

usage() {
  cat <<'EOF'
Start Postgres + km-agent (Docker) and optionally foreground OMLX, or run the backend with uv.

Usage:
  ./scripts/starter.sh [--dev] [--frontend]

  (no flags)     docker compose up -d km-agent (starts agent-db if needed). If OMLX is down and the
                 omlx CLI exists, runs `omlx serve` in the foreground.
  --dev          Starts only Postgres via Compose, then runs `uv sync` and execs AgentOS (requires uv).
                 Docker service km-agent must not be running (port 8000). OMLX must already respond.
  --dev --frontend
                 Same as --dev but AgentOS runs in the background; sets VITE_AGENT_OS_ORIGIN from
                 AGENT_OS_PORT, waits for GET /agents, then runs `npm run dev` in src/frontend.

Environment:
  KMA_MLX_BASE_URL, OMLX_PORT, OMLX_MODEL_DIR  See script header comments.
  KMA_AGENT_OS_HOST, KMA_AGENT_OS_PORT, KMA_VITE_PORT  See script header comments.
EOF
}

die() {
  echo "starter.sh: $*" >&2
  exit 1
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

require_curl() {
  have_cmd curl || die "curl not found (needed to probe the OMLX endpoint)."
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/compose.yaml"

MODE=docker
WITH_FRONTEND=0
for arg in "$@"; do
  case "$arg" in
    --dev) MODE=dev ;;
    --frontend) WITH_FRONTEND=1 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $arg (try --help)"
      ;;
  esac
done

if [[ "${WITH_FRONTEND}" == "1" && "${MODE}" != "dev" ]]; then
  die "--frontend requires --dev"
fi

FRONTEND_DIR="${REPO_ROOT}/src/frontend"

mlx_base="${KMA_MLX_BASE_URL:-http://127.0.0.1:7999/v1}"
mlx_base="${mlx_base%/}"
mlx_models_url="${mlx_base}/models"

require_docker_for_compose() {
  have_cmd docker || die "Docker CLI not found. Install Docker or use --dev with Postgres reachable."
  docker compose version >/dev/null 2>&1 || die "'docker compose' not available."
  [[ -f "${COMPOSE_FILE}" ]] || die "Missing ${COMPOSE_FILE}"
}

# Start agent-db (Postgres) only — used by --dev so the host uv process can use localhost:KMA_DB_PORT.
ensure_postgres_only() {
  require_docker_for_compose
  (
    cd "${REPO_ROOT}" || exit 1
    if docker compose ps --status running --services 2>/dev/null | grep -qx agent-db; then
      echo "Postgres (agent-db) is already running."
    else
      echo "Starting Postgres (agent-db) via docker compose..."
      docker compose up -d agent-db || die "docker compose up -d agent-db failed (is Docker running?)"
    fi
  )
}

# Start km-agent service (Compose will start agent-db if needed).
ensure_km_agent_docker() {
  require_docker_for_compose
  (
    cd "${REPO_ROOT}" || exit 1
    if docker compose ps --status running --services 2>/dev/null | grep -qx km-agent; then
      echo "km-agent (Docker) is already running."
    else
      echo "Starting km-agent (and dependencies) via docker compose..."
      docker compose up -d km-agent || die "docker compose up -d km-agent failed (is Docker running?)"
    fi
  )
}

docker_km_agent_running() {
  docker compose -f "${COMPOSE_FILE}" ps --status running --services 2>/dev/null | grep -qx km-agent
}

prepare_dev_backend() {
  ensure_postgres_only
  if docker_km_agent_running; then
    die "Docker service km-agent is running and would conflict with the uv backend on port 8000. Stop it with: (cd ${REPO_ROOT} && docker compose stop km-agent)"
  fi
  have_cmd uv || die "uv not found; install uv and run 'uv sync' from the repo root."
  require_curl
  if ! curl -fsS "${mlx_models_url}" >/dev/null 2>&1; then
    die "OMLX is not responding at ${mlx_base}. Start it first (e.g. ./scripts/starter.sh in another terminal), then retry --dev."
  fi
  cd "${REPO_ROOT}" || die "cannot cd to ${REPO_ROOT}"
  echo "starter.sh: uv sync (ensure ${REPO_ROOT}/.venv matches the project)..."
  uv sync --directory "${REPO_ROOT}" || die "uv sync failed"
  local venv_py="${REPO_ROOT}/.venv/bin/python"
  [[ -x "${venv_py}" ]] || die "starter.sh: expected ${venv_py} after uv sync"
  export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
  export AGENT_OS_HOST="${KMA_AGENT_OS_HOST:-${AGENT_OS_HOST:-127.0.0.1}}"
  export AGENT_OS_PORT="${KMA_AGENT_OS_PORT:-${AGENT_OS_PORT:-${PORT:-8000}}}"
  export RUNTIME_ENV="${RUNTIME_ENV:-dev}"
  export AGNO_DEBUG="${AGNO_DEBUG:-True}"
  DEV_VENV_PY="${venv_py}"
}

uv_run_app_main() {
  if [[ -f "${REPO_ROOT}/.env" ]]; then
    uv run --directory "${REPO_ROOT}" --python "${DEV_VENV_PY}" --env-file "${REPO_ROOT}/.env" python -m app.main
  else
    uv run --directory "${REPO_ROOT}" --python "${DEV_VENV_PY}" python -m app.main
  fi
}

run_dev_backend() {
  prepare_dev_backend
  echo "Starting AgentOS with ${DEV_VENV_PY} via uv run (foreground; Ctrl+C to stop)..."
  if [[ -f "${REPO_ROOT}/.env" ]]; then
    exec uv run --directory "${REPO_ROOT}" --python "${DEV_VENV_PY}" --env-file "${REPO_ROOT}/.env" python -m app.main
  else
    exec uv run --directory "${REPO_ROOT}" --python "${DEV_VENV_PY}" python -m app.main
  fi
}

run_dev_with_frontend() {
  prepare_dev_backend
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

  uv_run_app_main &
  BACKEND_PID=$!

  BACKEND_URL="http://127.0.0.1:${AGENT_OS_PORT}"
  export VITE_AGENT_OS_ORIGIN="${VITE_AGENT_OS_ORIGIN:-${BACKEND_URL}}"

  echo "AgentOS starting (${BACKEND_URL}, pid ${BACKEND_PID})..." >&2
  echo "Vite will proxy /agent-os → ${VITE_AGENT_OS_ORIGIN}" >&2

  ready=0
  for _ in $(seq 1 60); do
    if curl -sf "${BACKEND_URL}/agents" >/dev/null 2>&1; then
      ready=1
      break
    fi
    sleep 0.5
  done
  if [[ "${ready}" -ne 1 ]]; then
    echo "starter.sh: timed out waiting for GET ${BACKEND_URL}/agents; starting Vite anyway." >&2
  fi

  cd "${FRONTEND_DIR}" || die "cannot cd to ${FRONTEND_DIR}"
  npm run dev
}

if [[ "${MODE}" == "dev" ]]; then
  if [[ "${WITH_FRONTEND}" == "1" ]]; then
    run_dev_with_frontend
  else
    run_dev_backend
  fi
fi

# --- Docker stack (default) ---
ensure_km_agent_docker

if ! have_cmd omlx; then
  echo "starter.sh: omlx CLI not found. Install oMLX (https://github.com/jundot/omlx) if you need local models." >&2
  echo "Docker services are up; start OMLX separately when ready."
  exit 0
fi

require_curl
if curl -fsS "${mlx_models_url}" >/dev/null 2>&1; then
  echo "OMLX is already responding at ${mlx_base}. Docker stack is up; nothing else to start."
  exit 0
fi

export OMLX_PORT="${OMLX_PORT:-7999}"
export OMLX_MODEL_DIR="${OMLX_MODEL_DIR:-$HOME/.lmstudio/models}"
export OMLX_API_KEY="${OMLX_API_KEY:-localkey}"

echo "Starting OMLX at ${mlx_base} (foreground; Ctrl+C to stop)..."
echo "Model dir: ${OMLX_MODEL_DIR}"
exec omlx serve --model-dir="${OMLX_MODEL_DIR}"
