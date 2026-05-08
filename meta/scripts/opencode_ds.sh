#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OPENCODE_BIN="${OPENCODE_BIN:-$HOME/.opencode/bin/opencode}"
MODEL="${OPENCODE_MODEL:-openrouter/deepseek/deepseek-v4-flash}"
FORMAT="default"

usage() {
  cat <<'EOF' >&2
Usage:
  opencode_ds.sh [--json] [prompt-file]
  cat prompt.txt | opencode_ds.sh [--json]

Options:
  --json   Emit opencode JSON event stream
EOF
  exit 1
}

if [[ ! -x "${OPENCODE_BIN}" ]]; then
  echo "Missing opencode binary at ${OPENCODE_BIN}" >&2
  exit 1
fi

if [[ $# -gt 0 && "$1" == "--json" ]]; then
  FORMAT="json"
  shift
fi

if [[ $# -gt 1 ]]; then
  usage
fi

cd "${REPO_ROOT}"

if [[ $# -eq 1 ]]; then
  PROMPT="$(cat "$1")"
else
  PROMPT="$(cat)"
fi

if [[ -z "${PROMPT}" ]]; then
  echo "Prompt is empty." >&2
  exit 1
fi

exec "${OPENCODE_BIN}" run \
  --format "${FORMAT}" \
  -m "${MODEL}" \
  --dangerously-skip-permissions \
  "${PROMPT}"
