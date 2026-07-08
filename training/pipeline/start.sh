#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$ROOT"

echo "== Ninereeds MSM pipeline status =="
python3 meta/scripts/msm_orchestrator_status.py

echo
echo "== Waking MSM orchestrator =="
meta/scripts/wake_msm_orchestrator.sh
