#!/usr/bin/env bash
# Start local stack on macOS using Apple's native `container` CLI (not Docker Compose).
# Postgres (agent-db) runs in a container; AgentOS runs on the host via uv (--dev).
# OMLX stays on the host; this script can foreground `omlx serve` when needed.
#
# Prerequisites: macOS 26+, Apple Silicon, `container` CLI installed and on PATH
# (e.g. brew install container). Grant Local Network access if prompted.
# km-agent is NOT containerized on this path — use --dev for the uv backend.
#
# From the repository root:
#   ./scripts/starter-mac.sh                    # agent-db only, then OMLX if needed
#   ./scripts/starter-mac.sh --dev              # agent-db + uv backend
#   ./scripts/starter-mac.sh --dev --frontend   # same as --dev, then Vite chat UI
#
# Options:
#   --dev        Run `uv sync` then AgentOS with `uv run` using `.venv`. Requires uv; OMLX must respond.
#   --frontend   With --dev: start AgentOS in the background, wait for GET /agents, then `npm run dev`.
#   -h, --help
#
# Environment:
#   Loads ${KMA_ENV_FILE:-${REPO_ROOT}/.env} at startup (exports all variables). Copy example.env → .env if missing.
#   KMA_ENV_FILE  Alternate .env path (studies-hosted wrappers set this to assistants/km-agent/.env).
#   KMA_AGENT_DB_CONTAINER  Postgres container name (default: agent-db).
#   KMA_CONTAINER_POSTGRES_DATA  Host dir for Postgres data (default: ${REPO_ROOT}/.container-data/postgres)
#   KMA_MLX_BASE_URL  OMLX OpenAI-compatible base URL (default: http://127.0.0.1:7999/v1).
#   KMA_AGENT_OS_HOST (AGENT_OS_HOST)  Bind address for AgentOS (default: 127.0.0.1)
#   KMA_AGENT_OS_PORT (AGENT_OS_PORT, PORT)  AgentOS port (default: 8000)
#   KMA_VITE_PORT (VITE_PORT)  Vite dev port (default: 5174; read from src/frontend/.env if set)
#   RUNTIME_ENV, AGNO_DEBUG  Passed through to AgentOS (defaults: dev, True)

set -euo pipefail

usage() {
  cat <<'EOF'
Start Postgres (Apple container CLI) and optionally foreground OMLX, or run the backend with uv.

Usage:
  ./scripts/starter-mac.sh [--dev] [--frontend]

  (no flags)     Start agent-db via `container run`. If OMLX is down and the omlx CLI exists,
                 runs `omlx serve` in the foreground.
  --dev          Starts agent-db, then runs `uv sync` and execs AgentOS (requires uv).
                 OMLX must already respond.
  --dev --frontend
                 Same as --dev but AgentOS runs in the background; sets VITE_AGENT_OS_ORIGIN from
                 AGENT_OS_PORT, waits for GET /agents, then runs `npm run dev` in src/frontend.

Environment:
  KMA_CONTAINER_POSTGRES_DATA, KMA_DB_*  See script header comments.
  KMA_MLX_BASE_URL, OMLX_PORT, OMLX_MODEL_DIR  See script header comments.
  KMA_AGENT_OS_HOST, KMA_AGENT_OS_PORT, KMA_VITE_PORT  See script header comments.
EOF
}

die() {
  echo "starter-mac.sh: $*" >&2
  exit 1
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${KMA_ENV_FILE:-${REPO_ROOT}/.env}"
PG_IMAGE=docker.io/agnohq/pgvector:18

load_env_file() {
  if [[ ! -f "${1}" ]]; then
    echo "starter-mac.sh: no ${1} found (using environment defaults)."
    return 0
  fi
  echo "starter-mac.sh: loading ${1}..."
  set -a
  # shellcheck disable=SC1090
  source "${1}"
  set +a
}

mask_secret() {
  if [[ -n "${1:-}" ]]; then
    echo "***set***"
  else
    echo "(unset)"
  fi
}

echo_current_settings() {
  echo "--- Environment (from .env + shell) ---"
  echo "  KMA_REPO_ROOT=${REPO_ROOT}"
  echo "  KMA_LLM_PROVIDER=${KMA_LLM_PROVIDER:-<unset>}"
  echo "  KMA_LLM_MODEL_ID=${KMA_LLM_MODEL_ID:-<unset>}"
  echo "  KMA_LLM_BASE_URL=${KMA_LLM_BASE_URL:-<unset>}"
  echo "  KMA_EMBED_PROVIDER=${KMA_EMBED_PROVIDER:-<unset>}"
  echo "  KMA_EMBED_MODEL=${KMA_EMBED_MODEL:-<unset>}"
  echo "  KMA_EMBED_DIMENSIONS=${KMA_EMBED_DIMENSIONS:-<unset>}"
  echo "  KMA_CONTEXT_DIR=${KMA_CONTEXT_DIR:-<unset>}"
  echo "  KMA_DB_HOST=${KMA_DB_HOST:-${DB_HOST:-<unset>}}"
  echo "  KMA_DB_PORT=${KMA_DB_PORT:-${DB_PORT:-<unset>}}"
  echo "  KMA_DB_DATABASE=${KMA_DB_DATABASE:-${DB_DATABASE:-<unset>}}"
  echo "  KMA_DB_USER=${KMA_DB_USER:-${DB_USER:-<unset>}}"
  echo "  KMA_CONTAINER_POSTGRES_DATA=${KMA_CONTAINER_POSTGRES_DATA:-${REPO_ROOT}/.container-data/postgres}"
  echo "  KMA_AGENT_OS_HOST=${KMA_AGENT_OS_HOST:-${AGENT_OS_HOST:-<unset>}}"
  echo "  KMA_AGENT_OS_PORT=${KMA_AGENT_OS_PORT:-${AGENT_OS_PORT:-<unset>}}"
  echo "  KMA_VITE_PORT=${KMA_VITE_PORT:-${VITE_PORT:-<unset>}}"
  echo "  RUNTIME_ENV=${RUNTIME_ENV:-<unset>}"
  echo "  AGNO_DEBUG=${AGNO_DEBUG:-<unset>}"
  echo "  KMA_LLM_API_KEY=$(mask_secret "${KMA_LLM_API_KEY:-${OMLX_API_KEY:-}}")"
  echo "  KMA_PARALLEL_API_KEY=$(mask_secret "${KMA_PARALLEL_API_KEY:-${PARALLEL_API_KEY:-}}")"
  echo "  EXA_API_KEY=$(mask_secret "${EXA_API_KEY:-}")"
  echo "---------------------------------------"
}

MODE=default
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

load_env_file "${ENV_FILE}"
AGENT_DB_NAME="${KMA_AGENT_DB_CONTAINER:-agent-db}"
echo_current_settings

POSTGRES_DATA_DIR="${KMA_CONTAINER_POSTGRES_DATA:-${REPO_ROOT}/.container-data/postgres}"
FRONTEND_DIR="${REPO_ROOT}/src/frontend"

mlx_base="${KMA_LLM_BASE_URL:-http://localhost:7999/v1}"
mlx_base="${mlx_base%/}"
mlx_models_url="${mlx_base}/models"
mlx_api_key="${KMA_LLM_API_KEY:-${OMLX_API_KEY:-not-needed}}"

curl_mlx_models() {
  curl -fsS -H "Authorization: Bearer ${mlx_api_key}" "${mlx_models_url}"
}

omlx_models_reachable() {
  curl_mlx_models >/dev/null 2>&1
}

warn_docker_agent_db_conflict() {
  if ! have_cmd docker; then
    return 0
  fi
  if ! docker compose version >/dev/null 2>&1; then
    return 0
  fi
  if docker compose -f "${REPO_ROOT}/compose.yaml" ps --status running --services 2>/dev/null | grep -qx agent-db; then
    echo "starter-mac.sh: warning: Docker Compose agent-db is also running; port ${KMA_DB_PORT:-5432} may conflict." >&2
    echo "starter-mac.sh: stop it with: (cd ${REPO_ROOT} && docker compose stop agent-db)" >&2
  fi
}

require_container_cli() {
  have_cmd container || die "Apple container CLI not found (macOS 26+, Apple Silicon)."
}

ensure_container_system() {
  container system start || die "container system start failed"
}

wait_for_postgres() {
  local db_user="$1"
  local db_name="$2"
  echo "starter-mac.sh: waiting for Postgres to accept connections..."
  for _ in $(seq 1 30); do
    if container exec "${AGENT_DB_NAME}" pg_isready -U "${db_user}" -d "${db_name}" >/dev/null 2>&1; then
      echo "Postgres (${AGENT_DB_NAME}) is ready."
      return 0
    fi
    sleep 1
  done
  die "Postgres (${AGENT_DB_NAME}) did not become ready within 30s (check: container logs ${AGENT_DB_NAME})"
}

# Start agent-db (Postgres) via Apple container CLI — host uv connects via localhost:KMA_DB_PORT.
ensure_postgres_only() {
  require_container_cli
  ensure_container_system
  warn_docker_agent_db_conflict

  local db_port db_user db_pass db_name
  db_port="${KMA_DB_PORT:-5432}"
  db_user="${KMA_DB_USER:-ai}"
  db_pass="${KMA_DB_PASS:-ai}"
  db_name="${KMA_DB_DATABASE:-ai}"

  if container list -q 2>/dev/null | grep -qx "${AGENT_DB_NAME}"; then
    echo "Postgres (${AGENT_DB_NAME}) is already running."
  elif container list -a -q 2>/dev/null | grep -qx "${AGENT_DB_NAME}"; then
    echo "Starting stopped Postgres (${AGENT_DB_NAME})..."
    container start "${AGENT_DB_NAME}" || die "container start ${AGENT_DB_NAME} failed"
  else
    mkdir -p "${POSTGRES_DATA_DIR}"
    echo "Pulling ${PG_IMAGE} (first run may take a while)..."
    container image pull "${PG_IMAGE}" || die "container image pull ${PG_IMAGE} failed"
    echo "Starting Postgres (${AGENT_DB_NAME}) via container run..."
    container run -d \
      --name "${AGENT_DB_NAME}" \
      -p "127.0.0.1:${db_port}:5432/tcp" \
      -e "POSTGRES_USER=${db_user}" \
      -e "POSTGRES_PASSWORD=${db_pass}" \
      -e "POSTGRES_DB=${db_name}" \
      -v "${POSTGRES_DATA_DIR}:/var/lib/postgresql" \
      "${PG_IMAGE}" \
      || die "container run ${PG_IMAGE} failed"
  fi

  wait_for_postgres "${db_user}" "${db_name}"
}

prepare_dev_backend() {
  ensure_postgres_only
  have_cmd uv || die "uv not found; install uv and run 'uv sync' from the repo root."

  if ! omlx_models_reachable; then
    die "OMLX is not responding at ${mlx_base}. Start it first (e.g. ./scripts/starter-mac.sh in another terminal), then retry --dev."
  fi
  cd "${REPO_ROOT}" || die "cannot cd to ${REPO_ROOT}"
  echo "starter-mac.sh: uv sync (ensure ${REPO_ROOT}/.venv matches the project)..."
  uv sync --directory "${REPO_ROOT}" --extra local-mlx || die "uv sync failed"
  local venv_py="${REPO_ROOT}/.venv/bin/python"
  [[ -x "${venv_py}" ]] || die "starter-mac.sh: expected ${venv_py} after uv sync"
  export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
  export AGENT_OS_HOST="${KMA_AGENT_OS_HOST:-127.0.0.1}"
  export AGENT_OS_PORT="${KMA_AGENT_OS_PORT:-8000}"
  export RUNTIME_ENV="${RUNTIME_ENV:-dev}"
  export AGNO_DEBUG="${AGNO_DEBUG:-True}"
  DEV_VENV_PY="${venv_py}"
}

uv_run_app_main() {
  if [[ -f "${ENV_FILE}" ]]; then
    uv run --directory "${REPO_ROOT}" --python "${DEV_VENV_PY}" --env-file "${ENV_FILE}" python -m app.main
  else
    uv run --directory "${REPO_ROOT}" --python "${DEV_VENV_PY}" python -m app.main
  fi
}

run_dev_backend() {
  prepare_dev_backend
  echo "Starting AgentOS with ${DEV_VENV_PY} via uv run (foreground; Ctrl+C to stop)..."
  if [[ -f "${ENV_FILE}" ]]; then
    exec uv run --directory "${REPO_ROOT}" --python "${DEV_VENV_PY}" --env-file "${ENV_FILE}" python -m app.main
  else
    exec uv run --directory "${REPO_ROOT}" --python "${DEV_VENV_PY}" python -m app.main
  fi
}

ensure_frontend_deps() {
  have_cmd npm || die "npm not found; install Node.js to run the frontend."
  [[ -d "${FRONTEND_DIR}" ]] || die "frontend directory not found: ${FRONTEND_DIR}"
  if [[ -d "${FRONTEND_DIR}/node_modules" ]]; then
    return 0
  fi
  echo "starter-mac.sh: frontend dependencies missing; running npm ci in ${FRONTEND_DIR}..."
  (cd "${FRONTEND_DIR}" && npm ci) || die "npm ci failed in ${FRONTEND_DIR}"
}

run_dev_with_frontend() {
  prepare_dev_backend
  ensure_frontend_deps

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

  BACKEND_URL="http://${KMA_AGENT_OS_HOST}:${AGENT_OS_PORT}"
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
    echo "starter-mac.sh: timed out waiting for GET ${BACKEND_URL}/agents; starting Vite anyway." >&2
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

# --- Default: Postgres + optional OMLX foreground ---
ensure_postgres_only

if ! have_cmd omlx; then
  echo "starter-mac.sh: omlx CLI not found. Install oMLX (https://github.com/jundot/omlx) if you need local models." >&2
  echo "Postgres (${AGENT_DB_NAME}) is up; start OMLX separately when ready."
  exit 0
fi

if omlx_models_reachable; then
  echo "OMLX is already responding at ${mlx_base}. Postgres (${AGENT_DB_NAME}) is up; nothing else to start."
  exit 0
fi

export OMLX_PORT="${OMLX_PORT:-7999}"
export OMLX_MODEL_DIR="${OMLX_MODEL_DIR:-$HOME/.lmstudio/models}"
export OMLX_API_KEY="${OMLX_API_KEY:-localkey}"

echo "Starting OMLX at ${mlx_base} (foreground; Ctrl+C to stop)..."
echo "Model dir: ${OMLX_MODEL_DIR}"
exec omlx serve --model-dir="${OMLX_MODEL_DIR}"
