#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WORKERS=10
OUT_DIR="${REPO_ROOT}/tmp/opencode_fanout"

usage() {
  cat <<'EOF' >&2
Usage:
  opencode_ds_fanout.sh [--workers N] prompt1.txt [prompt2.txt ...]

Runs one opencode DeepSeek call per prompt file, in parallel.
Raw stdout/stderr for each prompt is written to tmp/opencode_fanout/.
EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workers)
      [[ $# -ge 2 ]] || usage
      WORKERS="$2"
      shift 2
      ;;
    --help|-h)
      usage
      ;;
    *)
      break
      ;;
  esac
done

[[ $# -ge 1 ]] || usage

mkdir -p "${OUT_DIR}"

run_one() {
  local prompt_file="$1"
  local base
  base="$(basename "${prompt_file}")"
  "${REPO_ROOT}/meta/scripts/opencode_ds.sh" --json "${prompt_file}" \
    > "${OUT_DIR}/${base}.jsonl" \
    2> "${OUT_DIR}/${base}.stderr"
}

export REPO_ROOT OUT_DIR
export -f run_one

printf '%s\n' "$@" | xargs -I{} -P "${WORKERS}" bash -lc 'run_one "$@"' _ {}
