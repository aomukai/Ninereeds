#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INTERVAL="${1:-1800}"
LOG_FILE="${REPO_ROOT}/tmp/lang_1_batches/monitor.log"

mkdir -p "${REPO_ROOT}/tmp/lang_1_batches"

while true; do
  ts="$(date -Iseconds)"
  files="$(find "${REPO_ROOT}/training_data/lang/lang_1" -maxdepth 1 -type f | wc -l)"
  ledger="$(wc -l < "${REPO_ROOT}/meta/ledgers/lang_1_progress.txt")"
  proc="$(ps -ef | rg -c "python3 ${REPO_ROOT}/meta/scripts/run_lang1_batch.py --batch-size 10 --max-tokens 16000" || true)"
  printf '%s files=%s ledger=%s active_workers=%s\n' "$ts" "$files" "$ledger" "$proc" >> "${LOG_FILE}"
  sleep "${INTERVAL}"
done
