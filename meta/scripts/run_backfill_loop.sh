#!/usr/bin/env bash
# Autonomous backfill loop.
# Iterates all 18 phase×POS queues in order (phase 1→6, nouns→verbs→adj).
# For each queue: generates prompts in batches of 3, runs 10 parallel DeepSeek
# workers, verifies written files, retries any missing words (up to 2 retries),
# then updates taught_words.txt and moves to the next queue.
#
# Usage:
#   ./meta/scripts/run_backfill_loop.sh [--start-phase N] [--start-pos nouns|verbs|adjectives]
#
# Logs to tmp/backfill_loop.log. Safe to interrupt and restart.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPTS="$REPO/meta/scripts"
PROMPTS="$REPO/tmp/backfill_prompts"
LOG="$REPO/tmp/backfill_loop.log"
WORKERS=10
BATCH=3
MAX_RETRIES=2

start_phase=1
start_pos="nouns"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --start-phase) start_phase="$2"; shift 2 ;;
        --start-pos)   start_pos="$2";   shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
mkdir -p "$PROMPTS" "$REPO/tmp/opencode_fanout"

PHASES=(1 2 3 4 5 6)
POSITIONS=(nouns verbs adjectives)

# Resolve start position index
pos_start_idx=0
for i in "${!POSITIONS[@]}"; do
    [[ "${POSITIONS[$i]}" == "$start_pos" ]] && pos_start_idx=$i
done

started=false
for phase in "${PHASES[@]}"; do
    for pos_idx in "${!POSITIONS[@]}"; do
        pos="${POSITIONS[$pos_idx]}"

        # Skip until we reach the start point
        if ! $started; then
            if [[ $phase -eq $start_phase && $pos_idx -ge $pos_start_idx ]]; then
                started=true
            elif [[ $phase -gt $start_phase ]]; then
                started=true
            else
                continue
            fi
        fi

        queue="$REPO/vocab/phase_${phase}_${pos}_new.txt"
        [[ -f "$queue" ]] || { log "SKIP: phase_${phase}_${pos} (no queue file)"; continue; }

        total=$(grep -c . "$queue" 2>/dev/null || echo 0)
        [[ "$total" -gt 0 ]] || { log "SKIP: phase_${phase}_${pos} (empty queue)"; continue; }

        log "=== phase_${phase} ${pos} ($total words in queue) ==="

        retries=0
        while true; do
            # Generate prompts for pending words
            rm -f "$PROMPTS/phase_${phase}_${pos}_"*.txt
            pending=$(python3 "$SCRIPTS/generate_backfill_prompts.py" \
                --phase "$phase" --pos "$pos" --batch-size "$BATCH" 2>&1)
            log "$pending"

            prompt_files=("$PROMPTS/phase_${phase}_${pos}_"*.txt)
            if [[ ! -e "${prompt_files[0]}" ]]; then
                log "  All words done for phase_${phase}_${pos}."
                break
            fi

            # Run fanout
            log "  Running ${#prompt_files[@]} prompt(s) with $WORKERS workers..."
            rm -f "$REPO/tmp/opencode_fanout/phase_${phase}_${pos}_"*.jsonl
            rm -f "$REPO/tmp/opencode_fanout/phase_${phase}_${pos}_"*.stderr
            "$SCRIPTS/opencode_ds_fanout.sh" --workers "$WORKERS" \
                "$PROMPTS/phase_${phase}_${pos}_"*.txt

            # Verify and record
            verify=$(python3 "$SCRIPTS/verify_backfill.py" --phase "$phase" --pos "$pos" 2>&1)
            log "$verify"

            # Check remaining count from full queue status line
            remaining_n=$(echo "$verify" | grep -oP '\d+(?= remaining)' | head -1 || echo "999")

            if [[ -z "$remaining_n" || "$remaining_n" -eq 0 ]]; then
                log "  phase_${phase}_${pos}: COMPLETE"
                break
            fi

            retries=$((retries + 1))
            if [[ $retries -ge $MAX_RETRIES ]]; then
                log "  WARNING: phase_${phase}_${pos}: $remaining after $MAX_RETRIES retries — moving on"
                break
            fi
            log "  Retrying ($retries/$MAX_RETRIES)..."
        done

        log "  Taught words updated."
    done
done

log "=== Backfill loop complete ==="
