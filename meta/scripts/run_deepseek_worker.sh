#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OPENCODE_BIN="${OPENCODE_BIN:-$HOME/.opencode/bin/opencode}"
MODEL="${OPENCODE_MODEL:-openrouter/deepseek/deepseek-v4-flash}"

if [[ ! -x "${OPENCODE_BIN}" ]]; then
  echo "Missing opencode binary at ${OPENCODE_BIN}" >&2
  exit 1
fi

cd "${REPO_ROOT}"

if [[ $# -gt 1 ]]; then
  echo "Usage: $0 [prompt-file]" >&2
  echo "Provide a prompt file or pipe the prompt on stdin." >&2
  exit 1
fi

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
  -m "${MODEL}" \
  --dangerously-skip-permissions \
  "${PROMPT}"
