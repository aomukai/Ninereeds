#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INTERVAL="${1:-1800}"
LOG_FILE="${REPO_ROOT}/tmp/lang_1_batches/monitor.log"
ALERT_FILE="${REPO_ROOT}/tmp/lang_1_batches/monitor.alerts.log"
STATE_FILE="${REPO_ROOT}/tmp/lang_1_batches/monitor.state"
LEDGER_FILE="${REPO_ROOT}/training_data/lang/lang_1/backfill_progress.txt"
MISMATCH_FILE="${REPO_ROOT}/training_data/mismatch.txt"
RUN_LOG="${REPO_ROOT}/tmp/lang_1_batches/run_lang1_all.setsid.log"
RUNNER_PATTERN="run_lang1_all.sh 10"

mkdir -p "${REPO_ROOT}/tmp/lang_1_batches"

count_valid_files() {
  python3 - <<'PY' "${REPO_ROOT}"
from pathlib import Path
import sys

root = Path(sys.argv[1])
out_dir = root / "training_data" / "lang" / "lang_1"
targets = {
    line.strip().replace(" ", "_")
    for line in (root / "training_data" / "mismatch.txt").read_text(encoding="utf-8").splitlines()
    if line.strip()
}
count = 0
for stem in targets:
    path = out_dir / f"{stem}.md"
    if not path.exists():
        continue
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        continue
    if len(lines) == 4 and all(line.strip() for line in lines):
        count += 1
print(count)
PY
}

last_log_line() {
  if [ -f "${RUN_LOG}" ]; then
    tail -n 1 "${RUN_LOG}"
  else
    printf ''
  fi
}

while true; do
  ts="$(date -Iseconds)"
  total_targets="$(wc -l < "${MISMATCH_FILE}")"
  ledger=0
  if [ -f "${LEDGER_FILE}" ]; then
    ledger="$(wc -l < "${LEDGER_FILE}")"
  fi
  valid_files="$(count_valid_files)"
  runner_proc="$(pgrep -af "${RUNNER_PATTERN}" || true)"
  runner_active=0
  if [ -n "${runner_proc}" ]; then
    runner_active=1
  fi
  remaining=$(( total_targets - ledger ))
  problems=()

  if [ "${ledger}" -ne "${valid_files}" ]; then
    problems+=("ledger_file_mismatch")
  fi

  if [ "${remaining}" -gt 0 ] && [ "${runner_active}" -eq 0 ]; then
    problems+=("runner_not_active")
  fi

  if [ -f "${RUN_LOG}" ] && rg -n "^FAILED batch " "${RUN_LOG}" >/dev/null 2>&1; then
    problems+=("failed_batch_logged")
  fi

  if [ -f "${STATE_FILE}" ]; then
    prev_ledger="$(cut -d' ' -f1 "${STATE_FILE}" 2>/dev/null || printf 0)"
    prev_ts="$(cut -d' ' -f2 "${STATE_FILE}" 2>/dev/null || printf 0)"
    now_epoch="$(date +%s)"
    if [ "${ledger}" -le "${prev_ledger}" ] && [ "${remaining}" -gt 0 ] && [ $(( now_epoch - prev_ts )) -ge "${INTERVAL}" ]; then
      problems+=("no_progress_last_interval")
    fi
  fi

  last_line="$(last_log_line)"
  if [ "${#problems[@]}" -eq 0 ]; then
    status="ok"
    problem_text="none"
  else
    status="problem"
    problem_text="$(IFS=,; printf '%s' "${problems[*]}")"
    printf '%s status=%s problems=%s ledger=%s valid_files=%s remaining=%s runner_active=%s last_log=%q\n' \
      "${ts}" "${status}" "${problem_text}" "${ledger}" "${valid_files}" "${remaining}" "${runner_active}" "${last_line}" >> "${ALERT_FILE}"
  fi

  printf '%s status=%s ledger=%s valid_files=%s remaining=%s runner_active=%s problems=%s last_log=%q\n' \
    "${ts}" "${status}" "${ledger}" "${valid_files}" "${remaining}" "${runner_active}" "${problem_text}" "${last_line}" >> "${LOG_FILE}"
  printf '%s %s\n' "${ledger}" "$(date +%s)" > "${STATE_FILE}"
  sleep "${INTERVAL}"
done
