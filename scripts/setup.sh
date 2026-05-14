#!/usr/bin/env bash
# Bootstrap local Docker Compose for km-agent.
#
# From a clone (uses origin URL + current branch when KMA_RAW_BASE is unset):
#   ./scripts/setup.sh
#
# One-liner (set KMA_RAW_BASE to your fork's raw root if not using the default):
#   curl -fsSL https://raw.githubusercontent.com/OWNER/REPO/BRANCH/scripts/setup.sh | bash
#
# Environment:
#   KMA_RAW_BASE   Root for raw.githubusercontent.com files (no trailing slash).
#                  Example: https://raw.githubusercontent.com/OWNER/REPO/main
#   KMA_TARGET_DIR Directory for compose.yaml (default: current directory).

set -euo pipefail

DEFAULT_RAW_BASE="${DEFAULT_RAW_BASE:-https://raw.githubusercontent.com/jbcodeforce/km-agent/main}"

die() {
  echo "setup.sh: $*" >&2
  exit 1
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

require_docker_cli() {
  have_cmd docker || die "Docker CLI not found. Install Docker: https://docs.docker.com/get-docker/"
  docker version >/dev/null 2>&1 || die "Docker daemon not reachable. Start Docker and retry."
}

require_docker_compose() {
  docker compose version >/dev/null 2>&1 || die "'docker compose' (Compose v2 plugin) not available. Install Docker Compose v2."
}

require_curl() {
  have_cmd curl || die "curl not found. Install curl or use a system that provides it."
}

# github.com/org/repo[.git] or git@github.com:org/repo[.git] -> org repo
parse_github_remote() {
  local url="$1"
  if [[ "$url" =~ ^git@github\.com:([^/]+)/([^/.]+)(\.git)?$ ]]; then
    printf '%s %s' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
    return 0
  fi
  if [[ "$url" =~ https?://github\.com/([^/]+)/([^/.]+)(\.git)?(/.*)?$ ]]; then
    printf '%s %s' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
    return 0
  fi
  return 1
}

raw_base_from_git() {
  local url org_repo org repo branch
  git rev-parse --git-dir >/dev/null 2>&1 || return 1
  url=$(git remote get-url origin 2>/dev/null) || return 1
  org_repo=$(parse_github_remote "$url") || return 1
  read -r org repo <<<"$org_repo"
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || return 1
  if [[ "$branch" == "HEAD" ]]; then
    branch="main"
  fi
  printf 'https://raw.githubusercontent.com/%s/%s/%s' "$org" "$repo" "$branch"
}

resolve_raw_base() {
  if [[ -n "${KMA_RAW_BASE:-}" ]]; then
    printf '%s' "${KMA_RAW_BASE%/}"
    return 0
  fi
  if rb=$(raw_base_from_git); then
    printf '%s' "$rb"
    return 0
  fi
  printf '%s' "${DEFAULT_RAW_BASE%/}"
}

download_compose() {
  local base target dir
  base=$(resolve_raw_base)
  dir=${KMA_TARGET_DIR:-.}
  target="${dir%/}/compose.yaml"
  mkdir -p "$dir"
  echo "Fetching compose.yaml from ${base}/compose.yaml"
  curl -fsSL "${base}/compose.yaml" -o "$target"
  echo "Wrote ${target}"
}

main() {
  require_docker_cli
  require_docker_compose
  require_curl
  download_compose
  echo "Next: copy example.env to .env, adjust variables, then from this directory run:"
  echo "  docker compose up -d agent-db"
}

main "$@"
