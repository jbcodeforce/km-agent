#!/usr/bin/env bash
# Start local dependencies for development: Postgres (Docker) and Ollama (native).
#
# Run from the repository root in a dedicated terminal; leave it running for Ollama:
#   ./scripts/starter.sh
#
# Environment:
#   OLLAMA_PORT  Host port for the Ollama HTTP API (default: 11434). Bound via OLLAMA_HOST for ollama serve.

set -euo pipefail

die() {
  echo "starter.sh: $*" >&2
  exit 1
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

require_curl() {
  have_cmd curl || die "curl not found (needed to probe the Ollama port)."
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/compose.yaml"

# Start agent-db (Postgres) if compose.yaml exists and the service is not already running.
ensure_postgres() {
  [[ -f "${COMPOSE_FILE}" ]] || return 0
  if ! have_cmd docker; then
    echo "starter.sh: docker not found; skipping Postgres (agent-db)." >&2
    return 0
  fi
  if ! docker compose version >/dev/null 2>&1; then
    echo "starter.sh: docker compose not available; skipping Postgres (agent-db)." >&2
    return 0
  fi
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

port="${OLLAMA_PORT:-11434}"
base="http://127.0.0.1:${port}"

ensure_postgres

if ! have_cmd ollama; then
  die "ollama CLI not found. Run ./scripts/setup.sh to install it, then retry."
fi

require_curl
if curl -fsS "${base}/api/tags" >/dev/null 2>&1; then
  echo "Ollama is already responding at ${base} (nothing to start)."
  exit 0
fi

echo "Starting Ollama at ${base} (foreground; Ctrl+C to stop)..."
export OLLAMA_HOST="127.0.0.1:${port}"
exec ollama serve
