#!/usr/bin/env bash
# Verify local agent stack: Postgres (Docker + TCP), DB endpoint, AgentOS backend,
# and optionally the Vite frontend.
#
# From repository root (loads .env when present):
#   ./scripts/verify_agent_env.sh
#   ./scripts/verify_agent_env.sh --frontend
#   ./scripts/verify_agent_env.sh --trace-env   # also print matching process env (secrets redacted)
#
# Environment (after optional .env load; prefer ``KMA_*``, legacy names still accepted):
#   KMA_DB_HOST, KMA_DB_PORT, KMA_DB_USER, KMA_DB_DATABASE, KMA_DB_PASS  (or legacy DB_*)
#   KMA_BACKEND_URL   Full base URL for AgentOS (overrides host/port below)
#   KMA_AGENT_OS_HOST, KMA_AGENT_OS_PORT  (or legacy AGENT_OS_* / PORT) — backend listen address
#   KMA_VITE_PORT     Frontend dev server port (or legacy VITE_PORT; default: 5174)
#   KMA_FRONTEND_URL  Full URL for frontend check (overrides default origin from KMA_VITE_PORT)
#   KMA_VERIFY_AGENT_DB_CONTAINER  Set to 0 to skip the docker compose agent-db check (legacy: VERIFY_AGENT_DB_CONTAINER).
#   KMA_VERIFY_TRACE_ENV           Set to 1 to dump all KMA_* process env (legacy: VERIFY_TRACE_ENV).

set -euo pipefail

usage() {
  cat <<'EOF'
Verify local agent stack: Postgres (Docker + TCP), DB endpoint, AgentOS backend,
and optionally the Vite frontend.

Usage:
  ./scripts/verify_agent_env.sh [--frontend|-f] [--trace-env]

Options:
  --frontend, -f   Also GET the Vite dev server (default http://127.0.0.1:<KMA_VITE_PORT>/; falls back to VITE_PORT; default port 5174).
  --trace-env        After the resolved summary, print every process variable whose name starts with KMA_ (secrets redacted).
  -h, --help       Show this help.

Always prints a short resolved-configuration trace using **KMA_** names (effective values; secrets redacted).

Loads REPO_ROOT/.env when present (same variables as example.env / kma.db).
EOF
}

die() {
  echo "verify_agent_env.sh: $*" >&2
  exit 1
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/compose.yaml"

CHECK_FRONTEND=0
TRACE_ENV_FULL=0
for arg in "$@"; do
  case "$arg" in
    --frontend|-f) CHECK_FRONTEND=1 ;;
    --trace-env) TRACE_ENV_FULL=1 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown option: $arg (try --help)"
      ;;
  esac
done

if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "${REPO_ROOT}/.env"
  set +a
fi

DB_HOST="${KMA_DB_HOST:-${DB_HOST:-localhost}}"
DB_PORT="${KMA_DB_PORT:-${DB_PORT:-5432}}"
DB_USER="${KMA_DB_USER:-${DB_USER:-ai}}"
DB_DATABASE="${KMA_DB_DATABASE:-${DB_DATABASE:-ai}}"
DB_PASS="${KMA_DB_PASS:-${DB_PASS:-ai}}"

BACKEND_PORT="${KMA_AGENT_OS_PORT:-${AGENT_OS_PORT:-${PORT:-8000}}}"
BACKEND_HOST="${KMA_AGENT_OS_HOST:-${AGENT_OS_HOST:-127.0.0.1}}"
if [[ -n "${KMA_BACKEND_URL:-}" ]]; then
  BACKEND_BASE="${KMA_BACKEND_URL%/}"
else
  BACKEND_BASE="http://${BACKEND_HOST}:${BACKEND_PORT}"
fi

FRONTEND_PORT="${KMA_VITE_PORT:-${VITE_PORT:-5174}}"
if [[ -n "${KMA_FRONTEND_URL:-}" ]]; then
  FRONTEND_BASE="${KMA_FRONTEND_URL%/}"
else
  FRONTEND_BASE="http://127.0.0.1:${FRONTEND_PORT}"
fi

mask_db_url() {
  echo "postgresql+psycopg://${DB_USER}:***@${DB_HOST}:${DB_PORT}/${DB_DATABASE}"
}

# True if env var NAME should not print raw values (passwords, tokens, API keys).
is_secret_env_name() {
  local n="$1"
  case "$n" in
    *PASSWORD* | KMA_DB_PASS | DB_PASS | *_SECRET | *_TOKEN | *_API_KEY | *GITHUB_ACCESS_TOKEN*)
      return 0
      ;;
  esac
  return 1
}

# Print a placeholder for secret values (length only) or the raw value for non-secrets.
format_env_value_for_trace() {
  local name="$1" val="$2"
  if is_secret_env_name "$name"; then
    if [[ -z "$val" ]]; then
      echo "<empty>"
    else
      echo "*** (${#val} chars)"
    fi
  else
    echo "$val"
  fi
}

trace_resolved_configuration() {
  echo "== Resolved configuration (KMA_* names; secrets redacted) =="
  if [[ -f "${REPO_ROOT}/.env" ]]; then
    echo "  .env: loaded from ${REPO_ROOT}/.env"
  else
    echo "  .env: absent (using defaults / inherited shell only)"
  fi
  echo "  REPO_ROOT=${REPO_ROOT}"
  echo "  KMA_VERIFY_AGENT_DB_CONTAINER=${KMA_VERIFY_AGENT_DB_CONTAINER:-${VERIFY_AGENT_DB_CONTAINER:-1}}"
  echo "  KMA_DB_HOST=${DB_HOST}  KMA_DB_PORT=${DB_PORT}  KMA_DB_USER=${DB_USER}  KMA_DB_DATABASE=${DB_DATABASE}"
  echo "  KMA_DB_PASS=$(format_env_value_for_trace KMA_DB_PASS "${DB_PASS}")"
  echo "  KMA DB URL (password hidden): $(mask_db_url)"
  echo "  KMA_BACKEND_URL=${KMA_BACKEND_URL:-<unset>}  effective BACKEND_BASE=${BACKEND_BASE}"
  echo "  KMA_AGENT_OS_HOST=${BACKEND_HOST}  KMA_AGENT_OS_PORT=${BACKEND_PORT}"
  echo "  KMA_FRONTEND_URL=${KMA_FRONTEND_URL:-<unset>}  effective FRONTEND_BASE=${FRONTEND_BASE}  KMA_VITE_PORT=${FRONTEND_PORT}"
  echo "  frontend_check=${CHECK_FRONTEND}  (1 = --frontend was passed)"
  echo "  KMA_LLM_PROVIDER=${KMA_LLM_PROVIDER:-<unset>}  KMA_EMBED_PROVIDER=${KMA_EMBED_PROVIDER:-<unset>}"
  echo "  OLLAMA_HOST=${OLLAMA_HOST:-<unset>}"
}

# Optional: dump every process variable whose name starts with KMA_ (values masked when sensitive).
trace_matching_process_env() {
  echo "== Process environment (KMA_* only; secrets redacted) =="
  local line key val
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" ]] && continue
    key="${line%%=*}"
    val="${line#*=}"
    [[ "$key" == "$line" ]] && continue
    case "$key" in
      KMA_*)
        printf '  %s=%s\n' "$key" "$(format_env_value_for_trace "$key" "$val")"
        ;;
    esac
  done < <(env | LC_ALL=C sort)
}

trace_environment() {
  trace_resolved_configuration
  if [[ "$TRACE_ENV_FULL" -eq 1 || "${KMA_VERIFY_TRACE_ENV:-${VERIFY_TRACE_ENV:-0}}" == "1" ]]; then
    trace_matching_process_env
  fi
}

tcp_open() {
  local host="$1" port="$2"
  if have_cmd nc; then
    nc -z -w 2 "$host" "$port" >/dev/null 2>&1
    return $?
  fi
  # bash /dev/tcp (no extra dependency)
  if bash -c "exec 3<>/dev/tcp/${host}/${port}" 2>/dev/null; then
    exec 3<&- 3>&- 2>/dev/null || true
    return 0
  fi
  return 1
}

check_postgres_container() {
  echo "== Postgres (Docker service agent-db) =="
  if [[ "${KMA_VERIFY_AGENT_DB_CONTAINER:-${VERIFY_AGENT_DB_CONTAINER:-1}}" == "0" ]]; then
    echo "  skipped (KMA_VERIFY_AGENT_DB_CONTAINER=0)."
    return 0
  fi
  if ! have_cmd docker; then
    echo "  docker: not installed — skip container check."
    return 0
  fi
  if ! docker compose version >/dev/null 2>&1; then
    echo "  docker compose: not available — skip container check."
    return 0
  fi
  if [[ ! -f "${COMPOSE_FILE}" ]]; then
    echo "  no compose.yaml at ${COMPOSE_FILE} — skip container check."
    return 0
  fi
  if docker compose -f "${COMPOSE_FILE}" ps --status running --services 2>/dev/null | grep -qx agent-db; then
    echo "  agent-db: running (docker compose)."
  else
    echo "  agent-db: NOT running. Start with: (cd ${REPO_ROOT} && docker compose up -d agent-db)" >&2
    return 1
  fi
}

check_db_tcp() {
  echo "== Database TCP (${DB_HOST}:${DB_PORT}) =="
  echo "  URL (password hidden): $(mask_db_url)"
  if tcp_open "$DB_HOST" "$DB_PORT"; then
    echo "  TCP: reachable."
  else
    echo "  TCP: not reachable on ${DB_HOST}:${DB_PORT}." >&2
    return 1
  fi
}

pg_ready_if_available() {
  echo "== PostgreSQL readiness (pg_isready, optional) =="
  if ! have_cmd pg_isready; then
    echo "  pg_isready: not installed — skip (optional)."
    return 0
  fi
  if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_DATABASE" -t 2 >/dev/null 2>&1; then
    echo "  pg_isready: accepts connections."
  else
    echo "  pg_isready: server not accepting connections (check credentials / DB name)." >&2
    return 1
  fi
}

check_backend() {
  echo "== AgentOS backend (${BACKEND_BASE}) =="
  have_cmd curl || die "curl not found (needed for HTTP checks)."
  local url="${BACKEND_BASE}/agents"
  local code
  code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null) || code="000"
  if [[ -z "$code" ]]; then
    code="000"
  fi
  if [[ "$code" == "200" ]]; then
    echo "  GET ${url} → HTTP ${code}"
  else
    echo "  GET ${url} → HTTP ${code} (expected 200)." >&2
    return 1
  fi
}

check_frontend() {
  echo "== Frontend (Vite) (${FRONTEND_BASE}) =="
  have_cmd curl || die "curl not found (needed for HTTP checks)."
  local url="${FRONTEND_BASE}/"
  local code
  code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null) || code="000"
  if [[ -z "$code" ]]; then
    code="000"
  fi
  if [[ "$code" == "200" || "$code" == "304" ]]; then
    echo "  GET ${url} → HTTP ${code}"
  else
    echo "  GET ${url} → HTTP ${code} (expected 200 or 304; is npm run dev running?)." >&2
    return 1
  fi
}

main() {
  trace_environment
  local ok=0
  check_postgres_container || ok=1
  check_db_tcp || ok=1
  pg_ready_if_available || ok=1
  check_backend || ok=1
  if [[ "$CHECK_FRONTEND" -eq 1 ]]; then
    check_frontend || ok=1
  fi
  if [[ "$ok" -ne 0 ]]; then
    die "one or more checks failed."
  fi
  echo "All checks passed."
}

main "$@"
