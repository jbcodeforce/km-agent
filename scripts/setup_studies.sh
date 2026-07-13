#!/usr/bin/env bash
# Scaffold assistants/km-agent/ inside a studies repository (e.g. ML-studies).
#
# From the km-agent repository root:
#   ./scripts/setup_studies.sh /path/to/ML-studies
#   ./scripts/setup_studies.sh /path/to/ML-studies --label ML-studies --force
#
# Options:
#   --label NAME   Studies label for manifests (default: directory basename)
#   --kma-home P   Path to km-agent clone (default: parent of this script's repo)
#   --force        Overwrite existing scaffold files
#   -h, --help

set -euo pipefail

usage() {
  cat <<'EOF'
Scaffold assistants/km-agent/ in a studies repository.

Usage:
  ./scripts/setup_studies.sh <studies-root> [--label NAME] [--kma-home PATH] [--force]

Creates:
  <studies-root>/assistants/km-agent/
    context/{raw,wiki,ontology}/
    example.env, .env, .kma-home
    starter-mac.sh, verify_config.sh, compile-docs.sh, README.md

After setup, from the studies repo:
  ./assistants/km-agent/starter-mac.sh --dev --frontend
EOF
}

die() {
  echo "setup_studies.sh: $*" >&2
  exit 1
}

slugify() {
  echo "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g'
}

render_template() {
  local src="$1"
  local dest="$2"
  sed \
    -e "s|__STUDIES_ROOT__|${STUDIES_ROOT}|g" \
    -e "s|__KMA_HOME__|${KMA_HOME}|g" \
    -e "s|__CONTEXT_DIR__|${CONTEXT_DIR}|g" \
    -e "s|__STUDIES_LABEL__|${STUDIES_LABEL}|g" \
    -e "s|__STUDIES_SLUG__|${STUDIES_SLUG}|g" \
    -e "s|__DB_CONTAINER__|${DB_CONTAINER}|g" \
    -e "s|__DB_PORT__|${DB_PORT}|g" \
    "${src}" > "${dest}"
}

write_file() {
  local rel="$1"
  local src="${TEMPLATE_DIR}/${rel}"
  local dest="${TARGET_DIR}/${rel}"
  [[ -f "${src}" ]] || die "missing template: ${src}"

  if [[ -f "${dest}" && "${FORCE}" -eq 0 ]]; then
    echo "setup_studies.sh: skip existing ${dest}"
    return 0
  fi

  mkdir -p "$(dirname "${dest}")"
  if [[ "${rel}" == *.sh ]]; then
    render_template "${src}" "${dest}"
    chmod +x "${dest}"
  else
    render_template "${src}" "${dest}"
  fi
  echo "setup_studies.sh: wrote ${dest}"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KMA_REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEMPLATE_DIR="${SCRIPT_DIR}/templates/studies"

STUDIES_ROOT=""
STUDIES_LABEL=""
KMA_HOME="${KMA_REPO_ROOT}"
FORCE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --label)
      [[ $# -ge 2 ]] || die "--label requires a value"
      STUDIES_LABEL="$2"
      shift 2
      ;;
    --kma-home)
      [[ $# -ge 2 ]] || die "--kma-home requires a path"
      KMA_HOME="$(cd "$2" && pwd)"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    -*)
      die "unknown option: $1"
      ;;
    *)
      if [[ -z "${STUDIES_ROOT}" ]]; then
        STUDIES_ROOT="$(cd "$1" && pwd)"
      else
        die "unexpected argument: $1"
      fi
      shift
      ;;
  esac
done

[[ -n "${STUDIES_ROOT}" ]] || die "studies root path required (see --help)"
[[ -d "${STUDIES_ROOT}" ]] || die "studies root not found: ${STUDIES_ROOT}"
[[ -f "${KMA_HOME}/scripts/starter-mac.sh" ]] || die "km-agent not found at KMA_HOME=${KMA_HOME}"

if [[ -z "${STUDIES_LABEL}" ]]; then
  STUDIES_LABEL="$(basename "${STUDIES_ROOT}")"
fi

STUDIES_SLUG="$(slugify "${STUDIES_LABEL}")"
[[ -n "${STUDIES_SLUG}" ]] || die "could not derive slug from label: ${STUDIES_LABEL}"

TARGET_DIR="${STUDIES_ROOT}/assistants/km-agent"
CONTEXT_DIR="${TARGET_DIR}/context"
DB_CONTAINER="kma-${STUDIES_SLUG}-db"
DB_PORT=5433

if [[ -d "${STUDIES_ROOT}/.git" ]]; then
  echo "setup_studies.sh: studies repo: ${STUDIES_ROOT}"
else
  echo "setup_studies.sh: warning: ${STUDIES_ROOT} is not a git repository" >&2
fi

mkdir -p "${TARGET_DIR}/context/raw" "${TARGET_DIR}/context/wiki" "${TARGET_DIR}/context/ontology"

for sub in raw wiki ontology; do
  touch "${TARGET_DIR}/context/${sub}/.gitkeep"
done

write_file "example.env"
write_file "starter-mac.sh"
write_file "verify_config.sh"
write_file "compile-docs.sh"
write_file "README.md"

if [[ -f "${TARGET_DIR}/.kma-home" && "${FORCE}" -eq 0 ]]; then
  echo "setup_studies.sh: skip existing ${TARGET_DIR}/.kma-home"
else
  printf '%s\n' "${KMA_HOME}" > "${TARGET_DIR}/.kma-home"
  echo "setup_studies.sh: wrote ${TARGET_DIR}/.kma-home"
fi

if [[ -f "${TARGET_DIR}/.env" && "${FORCE}" -eq 0 ]]; then
  echo "setup_studies.sh: skip existing ${TARGET_DIR}/.env (edit manually or use --force)"
else
  cp "${TARGET_DIR}/example.env" "${TARGET_DIR}/.env"
  echo "setup_studies.sh: wrote ${TARGET_DIR}/.env from example.env"
fi

cat <<EOF

Studies-hosted km-agent scaffold ready at:
  ${TARGET_DIR}

Next steps (from studies repo):
  1. Edit assistants/km-agent/.env (LLM keys, ports if needed)
  2. ./assistants/km-agent/starter-mac.sh --dev --frontend
  3. ./assistants/km-agent/verify_config.sh --frontend
  4. ./assistants/km-agent/compile-docs.sh --dry-run

Postgres container: ${DB_CONTAINER} on port ${DB_PORT}
Context directory:  ${CONTEXT_DIR}
Studies root:       ${STUDIES_ROOT}
km-agent clone:     ${KMA_HOME}
EOF
