#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MODE="auto"
RUNNER_ARGS=()

cd "$ROOT"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --status-only)
      MODE="status"
      ;;
    --orchestrator)
      MODE="orchestrator"
      ;;
    --dry-run-runner)
      RUNNER_ARGS+=("--dry-run")
      ;;
    --)
      shift
      RUNNER_ARGS+=("$@")
      break
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: training/pipeline/start.sh [--status-only|--orchestrator|--dry-run-runner] [-- runner args...]" >&2
      exit 2
      ;;
  esac
  shift
done

STATUS_FILE="$(mktemp)"
trap 'rm -f "$STATUS_FILE"' EXIT

load_status() {
  echo "== Ninereeds MSM pipeline status =="
  python3 meta/scripts/msm_orchestrator_status.py | tee "$STATUS_FILE"
}

status_field() {
  local field="$1"
  python3 - "$STATUS_FILE" "$field" <<'PY'
import json
import sys
data = json.loads(open(sys.argv[1], encoding="utf-8").read())
value = data.get(sys.argv[2])
print("" if value is None else value)
PY
}

wake_orchestrator() {
  echo
  echo "== Waking MSM orchestrator =="
  meta/scripts/wake_msm_orchestrator.sh
}

run_phase_block() {
  local phase_id="$1"
  if [[ -z "$phase_id" ]]; then
    echo "Cannot run phase block: current_phase_id is missing." >&2
    exit 2
  fi
  echo
  echo "== Running local MSM phase block: $phase_id =="
  python3 meta/scripts/msm_phase_runner.py --phase-id "$phase_id" "${RUNNER_ARGS[@]}"
}

load_status

if [[ "$MODE" == "status" ]]; then
  exit 0
fi

if [[ "$MODE" == "orchestrator" ]]; then
  wake_orchestrator
  exit $?
fi

next_action="$(status_field next_safe_action)"
current_phase="$(status_field current_phase_id)"

if [[ "$next_action" == "create_orchestrator_config" ]]; then
  echo
  echo "== Creating default MSM orchestrator config =="
  python3 meta/scripts/msm_bootstrap_config.py
  echo
  load_status
  next_action="$(status_field next_safe_action)"
  current_phase="$(status_field current_phase_id)"
fi

case "$next_action" in
  run_phase_block)
    run_phase_block "$current_phase"
    ;;
  stop)
    echo
    echo "== Pipeline paused by sentinel or Codex brake =="
    ;;
  create_or_repair_phase_registry|review_phase_gate|escalate_or_repair_block|review_session_report|review_update|decide_next_phase_action)
    wake_orchestrator
    ;;
  *)
    echo
    echo "== Unknown status action '$next_action'; waking orchestrator for a bounded decision =="
    wake_orchestrator
    ;;
esac
