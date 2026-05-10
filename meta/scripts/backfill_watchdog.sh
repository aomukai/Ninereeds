#!/usr/bin/env bash
# Watchdog for run_backfill_loop.sh.
# Checks every CHECK_INTERVAL seconds; logs status; restarts loop if dead.
# Exits cleanly when backfill is complete.
#
# Usage:
#   nohup ./meta/scripts/backfill_watchdog.sh >> tmp/backfill_watchdog.log 2>&1 &

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOOP_SCRIPT="$REPO/meta/scripts/run_backfill_loop.sh"
LOOP_LOG="$REPO/tmp/backfill_loop.log"
PROGRESS="$REPO/training_data/phases/backfill_progress.txt"
WATCHDOG_LOG="$REPO/tmp/backfill_watchdog.log"
CHECK_INTERVAL=120  # seconds

PHASES=(1 2 3 4 5 6)
POSITIONS=(nouns verbs adjectives)

wlog() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$WATCHDOG_LOG"; }

# Advance to next phase/pos after the given one
next_queue() {
    local phase="$1" pos="$2"
    local pos_idx=0
    for i in "${!POSITIONS[@]}"; do
        [[ "${POSITIONS[$i]}" == "$pos" ]] && pos_idx=$i
    done
    local next_pos_idx=$(( pos_idx + 1 ))
    if [[ $next_pos_idx -lt ${#POSITIONS[@]} ]]; then
        echo "$phase ${POSITIONS[$next_pos_idx]}"
    else
        local next_phase=$(( phase + 1 ))
        if [[ $next_phase -le 6 ]]; then
            echo "$next_phase nouns"
        else
            echo "done"
        fi
    fi
}

# Determine restart point from loop log
restart_point() {
    # Find the last phase that was started
    local last_line
    last_line=$(grep "=== phase_" "$LOOP_LOG" 2>/dev/null | tail -1) || true
    if [[ -z "$last_line" ]]; then
        echo "1 nouns"; return
    fi

    local phase pos
    phase=$(echo "$last_line" | grep -oP '(?<=phase_)\d+' | head -1)
    pos=$(echo "$last_line" | grep -oP 'nouns|verbs|adjectives' | head -1)

    # If that phase/pos shows COMPLETE in the log, advance to next
    if grep -q "phase_${phase}_${pos}: COMPLETE" "$LOOP_LOG" 2>/dev/null; then
        next_queue "$phase" "$pos"
    else
        echo "$phase $pos"
    fi
}

wlog "=== Watchdog started (PID $$, checking every ${CHECK_INTERVAL}s) ==="

while true; do
    sleep "$CHECK_INTERVAL"

    # Status snapshot
    done_count=0
    [[ -f "$PROGRESS" ]] && done_count=$(wc -l < "$PROGRESS")

    # Check for completion
    if grep -q "Backfill loop complete" "$LOOP_LOG" 2>/dev/null; then
        wlog "Backfill complete. $done_count words done. Watchdog exiting."
        exit 0
    fi

    # Check if loop is alive
    if pgrep -f "run_backfill_loop.sh" > /dev/null 2>&1; then
        current=$(grep "=== phase_" "$LOOP_LOG" 2>/dev/null | tail -1 | sed 's/^\[.*\] //' || echo "unknown")
        wlog "OK — $done_count words done. Current: $current"
        continue
    fi

    # Loop is dead and not complete — restart
    wlog "Loop not running! $done_count words done. Restarting..."

    read -r r_phase r_pos <<< "$(restart_point)"

    if [[ "$r_phase" == "done" ]]; then
        wlog "All queues appear complete. Watchdog exiting."
        exit 0
    fi

    wlog "Restarting from --start-phase $r_phase --start-pos $r_pos"
    nohup bash "$LOOP_SCRIPT" --start-phase "$r_phase" --start-pos "$r_pos" >> "$LOOP_LOG" 2>&1 &
    wlog "Loop restarted with PID $!"
done
