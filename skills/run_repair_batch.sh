#!/usr/bin/env bash
# Full repair run — loops until damage_map.txt is exhausted.
# Usage: bash skills/run_repair_batch.sh [batch_size]
# Default batch size: 30
# Log: meta/repair_run.log

set -euo pipefail

BATCH=${1:-30}
LOG="meta/repair_run.log"
DAMAGE_MAP="training_data/phases/damage_map.txt"

cd "$(dirname "$0")/.."

echo "=== Repair run started $(date) ===" | tee -a "$LOG"
echo "Batch size: $BATCH" | tee -a "$LOG"

while true; do
    remaining=$(grep -c "\.md" "$DAMAGE_MAP" 2>/dev/null || echo 0)
    if [ "$remaining" -eq 0 ]; then
        echo "$(date) — damage_map.txt empty. Done." | tee -a "$LOG"
        break
    fi

    echo "$(date) — $remaining entries remaining, running batch of $BATCH..." | tee -a "$LOG"
    python3 skills/worker_repair.py --batch "$BATCH" 2>&1 | tee -a "$LOG"

    # Brief pause between batches
    sleep 2
done

echo "=== Repair run finished $(date) ===" | tee -a "$LOG"
