#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_DIR="${REPO_ROOT}/tmp/lang_1_batches"
BATCH_SIZE="${1:-5}"
TIMEOUT="${LANG1_TIMEOUT:-1800}"
MAX_TOKENS="${LANG1_MAX_TOKENS:-16000}"
RETRY_MAX_TOKENS="${LANG1_RETRY_MAX_TOKENS:-32000}"

mkdir -p "${LOG_DIR}"

while true; do
  ts="$(date +%Y%m%d_%H%M%S)"
  log="${LOG_DIR}/nonsense_repair_loop_${ts}.log"
  python3 "${SCRIPT_DIR}/repair_lang1_nonsense_batch.py" \
    --batch-size "${BATCH_SIZE}" \
    --timeout "${TIMEOUT}" \
    --max-tokens "${MAX_TOKENS}" \
    --retry-max-tokens "${RETRY_MAX_TOKENS}" | tee "${log}"

  if grep -q "^number of files repaired: 0$" "${log}"; then
    break
  fi
done
