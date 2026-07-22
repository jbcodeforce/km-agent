#!/usr/bin/env bash
# Verify km-agent configuration and local stack health.
#
# From repository root (loads .env when present):
#   ./scripts/verify_config.sh
#   ./scripts/verify_config.sh --frontend
#   ./scripts/verify_config.sh --trace-env
#
# Checks: resolved KMA_* settings, Postgres (Docker + TCP), AgentOS backend,
# LLM /v1/models (mlx/ollama), and optionally the Vite frontend.

set -euo pipefail

usage() {
  cat <<'EOF'
Verify km-agent configuration and local stack health.

Usage:
  ./scripts/verify_config.sh [--frontend|-f] [--trace-env]

Options:
  --frontend, -f   Also GET the Vite dev server (default http://127.0.0.1:<KMA_VITE_PORT>/).
  --trace-env      After the resolved summary, print every KMA_* process variable (secrets redacted).
  -h, --help       Show this help.

Always prints resolved configuration (KMA_* names; secrets redacted), then runs connectivity checks.
Loads ${KMA_ENV_FILE:-REPO_ROOT/.env} when present (same variables as example.env / kma.config).

Environment (prefer KMA_*):
  KMA_DB_HOST, KMA_DB_PORT, KMA_DB_USER, KMA_DB_DATABASE, KMA_DB_PASS  (or DB_*)
  KMA_BACKEND_URL, KMA_AGENT_OS_HOST, KMA_AGENT_OS_PORT
  KMA_VITE_PORT, KMA_FRONTEND_URL
  KMA_LLM_PROVIDER, KMA_LLM_MODEL_ID, KMA_LLM_BASE_URL, KMA_LLM_HOST, KMA_LLM_PORT, KMA_LLM_API_KEY
  KMA_EMBED_PROVIDER, KMA_EMBED_MODEL, KMA_EMBED_BASE_URL, KMA_EMBED_DIMENSIONS
  KMA_VERIFY_AGENT_DB_CONTAINER  Set to 0 to skip docker compose agent-db check.
  KMA_VERIFY_TRACE_ENV           Set to 1 to dump all KMA_* process env.
EOF
}

die() {
  echo "" >&2
  echo "✗  $*" >&2
  exit 1
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

# --- user-facing output -------------------------------------------------------
section() {
  echo ""
  echo "── $* ──"
}

ok() {
  echo "  ✓  $*"
}

fail() {
  echo "  ✗  $*" >&2
}

warn() {
  echo "  !  $*" >&2
}

skip() {
  echo "  –  $*"
}

info() {
  echo "  ·  $*"
}

hint() {
  echo "     → $*" >&2
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/compose.yaml"
ENV_FILE="${KMA_ENV_FILE:-${REPO_ROOT}/.env}"

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
      die "Unknown option: $arg (try --help)"
      ;;
  esac
done

load_env_file() {
  if [[ ! -f "${1}" ]]; then
    return 0
  fi
  info "Loading ${1}"
  set -a
  # shellcheck disable=SC1090
  source "${1}"
  set +a
}

strip_quotes() {
  local v="$1"
  v="${v#\"}"
  v="${v%\"}"
  v="${v#\'}"
  v="${v%\'}"
  printf '%s' "$v"
}

DB_HOST="${KMA_DB_HOST:-localhost}"
DB_PORT="${KMA_DB_PORT:-5432}"
DB_USER="${KMA_DB_USER:-ai}"
DB_DATABASE="${KMA_DB_DATABASE:-ai}"
DB_PASS="${KMA_DB_PASS:-ai}"

BACKEND_PORT="${KMA_AGENT_OS_PORT:-8000}"
BACKEND_HOST="${KMA_AGENT_OS_HOST:-127.0.0.1}"
if [[ -n "${KMA_BACKEND_URL:-}" ]]; then
  BACKEND_BASE="${KMA_BACKEND_URL%/}"
else
  BACKEND_BASE="http://${BACKEND_HOST}:${BACKEND_PORT}"
fi

FRONTEND_PORT="${KMA_VITE_PORT:-5174}"
if [[ -n "${KMA_FRONTEND_URL:-}" ]]; then
  FRONTEND_BASE="${KMA_FRONTEND_URL%/}"
else
  FRONTEND_BASE="http://127.0.0.1:${FRONTEND_PORT}"
fi

resolve_llm_base_url() {
  local raw host port base
  raw="${KMA_LLM_BASE_URL:-}"
  if [[ -n "$raw" ]]; then
    base="$(strip_quotes "$raw")"
    base="${base%/}"
    if [[ "$base" != */v1 ]]; then
      base="${base}/v1"
    fi
    printf '%s' "$base"
    return 0
  fi
  host="$(strip_quotes "${KMA_LLM_HOST:-127.0.0.1}")"
  port="$(strip_quotes "${KMA_LLM_PORT:-7999}")"
  if [[ "$host" == http://* || "$host" == https://* ]]; then
    base="${host%/}"
    if [[ "$base" != */v1 ]]; then
      base="${base}/v1"
    fi
  else
    base="http://${host}:${port}/v1"
  fi
  printf '%s' "$base"
}

resolve_embed_base_url() {
  local raw base
  raw="${KMA_EMBED_BASE_URL:-}"
  if [[ -n "$raw" ]]; then
    base="$(strip_quotes "$raw")"
    base="${base%/}"
    if [[ "$base" != */v1 ]]; then
      base="${base}/v1"
    fi
    printf '%s' "$base"
    return 0
  fi
  resolve_llm_base_url
}

resolve_models_base_url() {
  local llm_provider="${KMA_LLM_PROVIDER:-mlx}"
  case "$llm_provider" in
    mlx | ollama)
      resolve_llm_base_url
      return 0
      ;;
  esac
  if [[ "${KMA_EMBED_PROVIDER:-}" == "mlx" ]]; then
    resolve_embed_base_url
    return 0
  fi
  resolve_llm_base_url
}

mask_db_url() {
  echo "postgresql+psycopg://${DB_USER}:***@${DB_HOST}:${DB_PORT}/${DB_DATABASE}"
}

is_secret_env_name() {
  local n="$1"
  case "$n" in
    *PASSWORD* | KMA_DB_PASS | DB_PASS | *_SECRET | *_TOKEN | *_API_KEY | *GITHUB_ACCESS_TOKEN*)
      return 0
      ;;
  esac
  return 1
}

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
  local llm_base embed_base
  llm_base="$(resolve_llm_base_url)"
  embed_base="$(resolve_embed_base_url)"
  section "Resolved configuration"
  info "Secrets are redacted. Effective values shown after → when they differ from the env var."
  if [[ -f "${ENV_FILE}" ]]; then
    info ".env: ${ENV_FILE}"
  else
    info ".env: not found (defaults / inherited shell only)"
  fi
  info "repo:  ${REPO_ROOT}"
  info "check Docker agent-db: ${KMA_VERIFY_AGENT_DB_CONTAINER:-${VERIFY_AGENT_DB_CONTAINER:-1}}"
  echo ""
  echo "  Database"
  info "host=${DB_HOST}  port=${DB_PORT}  user=${DB_USER}  database=${DB_DATABASE}"
  info "password=$(format_env_value_for_trace KMA_DB_PASS "${DB_PASS}")"
  info "url=$(mask_db_url)"
  echo ""
  echo "  Backend"
  info "KMA_BACKEND_URL=${KMA_BACKEND_URL:-<unset>}  → ${BACKEND_BASE}"
  info "host=${BACKEND_HOST}  port=${BACKEND_PORT}"
  echo ""
  echo "  Frontend"
  info "KMA_FRONTEND_URL=${KMA_FRONTEND_URL:-<unset>}  → ${FRONTEND_BASE}"
  info "Vite port=${FRONTEND_PORT}  (--frontend check: $([[ "$CHECK_FRONTEND" -eq 1 ]] && echo on || echo off))"
  echo ""
  echo "  LLM"
  info "provider=${KMA_LLM_PROVIDER:-<unset>}"
  info "model=${KMA_LLM_MODEL_ID:-${KMA_COMPILER_MODEL_ID:-${KMA_MODEL_ID:-<unset>}}}"
  info "KMA_LLM_BASE_URL=${KMA_LLM_BASE_URL:-<unset>}  → ${llm_base}"
  info "host=${KMA_LLM_HOST:-${LLM_HOST:-<unset>}}  port=${KMA_LLM_PORT:-${LLM_PORT:-<unset>}}"
  info "api_key=$(format_env_value_for_trace KMA_LLM_API_KEY "${KMA_LLM_API_KEY:-${OMLX_API_KEY:-}}")"
  echo ""
  echo "  Embeddings"
  info "provider=${KMA_EMBED_PROVIDER:-<unset>}  model=${KMA_EMBED_MODEL:-<unset>}"
  info "KMA_EMBED_BASE_URL=${KMA_EMBED_BASE_URL:-<unset>}  → ${embed_base}"
  info "dimensions=${KMA_EMBED_DIMENSIONS:-<unset>}"
}

trace_matching_process_env() {
  section "Process environment (KMA_* only)"
  local line key val count=0
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" ]] && continue
    key="${line%%=*}"
    val="${line#*=}"
    [[ "$key" == "$line" ]] && continue
    case "$key" in
      KMA_*)
        printf '  ·  %s=%s\n' "$key" "$(format_env_value_for_trace "$key" "$val")"
        count=$((count + 1))
        ;;
    esac
  done < <(env | LC_ALL=C sort)
  if [[ "$count" -eq 0 ]]; then
    skip "No KMA_* variables in the process environment"
  fi
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
  if bash -c "exec 3<>/dev/tcp/${host}/${port}" 2>/dev/null; then
    exec 3<&- 3>&- 2>/dev/null || true
    return 0
  fi
  return 1
}

check_postgres_container() {
  section "Postgres container (agent-db)"
  if [[ "${KMA_VERIFY_AGENT_DB_CONTAINER:-${VERIFY_AGENT_DB_CONTAINER:-1}}" == "0" ]]; then
    skip "Skipped (KMA_VERIFY_AGENT_DB_CONTAINER=0)"
    return 0
  fi
  if ! have_cmd docker; then
    skip "Docker not installed — container check skipped"
    return 0
  fi
  if ! docker compose version >/dev/null 2>&1; then
    skip "docker compose not available — container check skipped"
    return 0
  fi
  if [[ ! -f "${COMPOSE_FILE}" ]]; then
    skip "No compose.yaml at ${COMPOSE_FILE} — container check skipped"
    return 0
  fi
  if docker compose -f "${COMPOSE_FILE}" ps --status running --services 2>/dev/null | grep -qx agent-db; then
    ok "agent-db is running"
  else
    fail "agent-db is not running"
    hint "Start it: (cd ${REPO_ROOT} && docker compose up -d agent-db)"
    return 1
  fi
}

check_db_tcp() {
  section "Database TCP (${DB_HOST}:${DB_PORT})"
  info "url=$(mask_db_url)"
  if tcp_open "$DB_HOST" "$DB_PORT"; then
    ok "Port is open"
  else
    fail "Cannot connect to ${DB_HOST}:${DB_PORT}"
    hint "Is Postgres up? Check agent-db or KMA_DB_HOST / KMA_DB_PORT."
    return 1
  fi
}

pg_ready_if_available() {
  section "PostgreSQL readiness (optional)"
  if ! have_cmd pg_isready; then
    skip "pg_isready not installed — optional check skipped"
    return 0
  fi
  if pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_DATABASE" -t 2 >/dev/null 2>&1; then
    ok "Server accepts connections (user=${DB_USER} db=${DB_DATABASE})"
  else
    fail "Server is not accepting connections"
    hint "Check credentials and database name (KMA_DB_USER / KMA_DB_DATABASE)."
    return 1
  fi
}

check_backend() {
  section "AgentOS backend"
  have_cmd curl || die "curl is required for HTTP checks (not found in PATH)."
  local url="${BACKEND_BASE}/agents"
  local code
  code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null) || code="000"
  if [[ -z "$code" ]]; then
    code="000"
  fi
  if [[ "$code" == "200" ]]; then
    ok "GET ${url} → HTTP ${code}"
  else
    fail "GET ${url} → HTTP ${code} (expected 200)"
    hint "Is the backend running at ${BACKEND_BASE}?"
    return 1
  fi
}

check_frontend() {
  section "Frontend (Vite)"
  have_cmd curl || die "curl is required for HTTP checks (not found in PATH)."
  local url="${FRONTEND_BASE}/"
  local code
  code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null) || code="000"
  if [[ -z "$code" ]]; then
    code="000"
  fi
  if [[ "$code" == "200" || "$code" == "304" ]]; then
    ok "GET ${url} → HTTP ${code}"
  else
    fail "GET ${url} → HTTP ${code} (expected 200 or 304)"
    hint "Start the UI with: npm run dev"
    return 1
  fi
}

list_models_from_json() {
  # Use -c (not a heredoc): a heredoc replaces stdin and would swallow piped JSON.
  python3 -c '
import json
import sys

raw = sys.stdin.read().strip()
if not raw:
    print("  (empty response body)")
    raise SystemExit(0)

try:
    payload = json.loads(raw)
except json.JSONDecodeError as exc:
    print(f"  (could not parse JSON: {exc})")
    raise SystemExit(0)

items = payload.get("data")
if items is None and isinstance(payload, list):
    items = payload
if not items:
    print("  (no models reported)")
    raise SystemExit(0)

for item in items:
    if isinstance(item, dict):
        model_id = item.get("id") or item.get("name") or item.get("model")
        if model_id:
            print(f"  - {model_id}")
            continue
    print(f"  - {item}")
'
}

needs_llm_models_check() {
  local llm_provider="${KMA_LLM_PROVIDER:-ollama}"
  case "$llm_provider" in
    mlx | ollama) return 0 ;;
  esac
  [[ "${KMA_EMBED_PROVIDER:-}" == "mlx" ]]
}

check_llm_models() {
  local llm_provider models_base models_url api_key response body code
  local chat_id embed_id ok=0

  if ! needs_llm_models_check; then
    section "LLM models"
    skip "Skipped for provider=${KMA_LLM_PROVIDER:-<unset>} (/v1/models is for mlx, ollama, or KMA_EMBED_PROVIDER=mlx)"
    return 0
  fi

  have_cmd curl || die "curl is required for the LLM model check (not found in PATH)."
  llm_provider="${KMA_LLM_PROVIDER:-ollama}"
  models_base="$(resolve_models_base_url)"
  models_url="${models_base}/models"
  api_key="$(strip_quotes "${KMA_LLM_API_KEY:-${OMLX_API_KEY:-not-needed}}")"

  section "LLM models"
  info "endpoint=${models_url}"
  response=""
  body=""
  code="000"
  response="$(curl -sS --max-time 10 -w $'\n%{http_code}' -H "Authorization: Bearer ${api_key}" "${models_url}" 2>/dev/null)" || response=""
  if [[ -n "$response" ]]; then
    code="${response##*$'\n'}"
    body="${response%$'\n'*}"
  fi
  if [[ "$code" != "200" ]]; then
    fail "GET ${models_url} → HTTP ${code}"
    hint "Is the LLM server running? (mlx / ollama)"
    return 1
  fi
  ok "GET ${models_url} → HTTP 200"
  info "Deployed models:"
  printf '%s\n' "$body" | list_models_from_json

  if [[ "$llm_provider" == "mlx" || "$llm_provider" == "ollama" ]]; then
    chat_id="$(strip_quotes "${KMA_LLM_MODEL_ID:-${KMA_COMPILER_MODEL_ID:-${KMA_MODEL_ID:-}}}")"
    if [[ -z "$chat_id" ]]; then
      fail "Chat model not set (KMA_LLM_MODEL_ID)"
      ok=1
    elif printf '%s' "$body" | grep -qF "\"${chat_id}\""; then
      ok "Chat model available: ${chat_id}"
    else
      fail "Chat model not in /models: ${chat_id}"
      hint "Load this model into the LLM server, or fix KMA_LLM_MODEL_ID."
      ok=1
    fi
  fi

  if [[ "${KMA_EMBED_PROVIDER:-}" == "mlx" ]]; then
    embed_id="$(strip_quotes "${KMA_EMBED_MODEL:-}")"
    if [[ -z "$embed_id" ]]; then
      fail "Embed model not set (KMA_EMBED_MODEL required when KMA_EMBED_PROVIDER=mlx)"
      ok=1
    elif printf '%s' "$body" | grep -qF "\"${embed_id}\""; then
      ok "Embed model available: ${embed_id}"
    else
      warn "Embed model not in /models yet: ${embed_id}"
      hint "Load it into OMLX when ready (does not fail this check)."
    fi
  fi

  return "$ok"
}

main() {
  echo ""
  echo "km-agent configuration check"
  load_env_file "${ENV_FILE}"
  trace_environment
  local failed=0
  # check_postgres_container || failed=1
  check_db_tcp || failed=1
  pg_ready_if_available || failed=1
  check_backend || failed=1
  check_llm_models || failed=1
  if [[ "$CHECK_FRONTEND" -eq 1 ]]; then
    check_frontend || failed=1
  fi
  echo ""
  if [[ "$failed" -ne 0 ]]; then
    die "One or more checks failed. See ✗ lines above."
  fi
  echo "✓  All checks passed."
  echo ""
}

main "$@"
