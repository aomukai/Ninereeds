#!/usr/bin/env bash
# angle_aug_monitor.sh — check progress every 30 min, restart dead workers.
# Run once: bash meta/scripts/angle_aug_monitor.sh &

REPO="/media/aomukai/SSD External/Ninereeds"
LOG="$REPO/tmp/aug_rephrase_monitor.log"
ENV="$REPO/.env"
SCRIPT="$REPO/meta/scripts/angle_aug.py"
DONE_FILE="$REPO/training_data/redesign/aug_done.txt"
TOTAL=33966
WAVE=1
WORKERS=4

mkdir -p "$REPO/tmp"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

is_running() {
    pgrep -f "angle_aug.py gen --source openrouter" > /dev/null 2>&1
}

restart_worker() {
    log "RESTART: openrouter (workers=$WORKERS, wave=$WAVE)"
    (cd "$REPO" && set -a && source "$ENV" && set +a \
        && python3 "$SCRIPT" gen --wave "$WAVE" --source openrouter --workers "$WORKERS" \
        >> "$REPO/tmp/aug_rephrase_openrouter.log" 2>&1) &
    log "RESTART: launched (PID $!)"
}

log "Monitor started. Checking every 30 minutes. Total=$TOTAL wave=$WAVE"

while true; do
    sleep 1800

    done_count=$(wc -l < "$DONE_FILE" 2>/dev/null || echo 0)
    log "=== check === done=$done_count / $TOTAL"

    if [ "$done_count" -ge "$TOTAL" ]; then
        log "All $TOTAL files complete. Monitor exiting."
        break
    fi

    if is_running; then
        log "OK: openrouter worker running"
    else
        log "DEAD: openrouter worker gone — restarting"
        restart_worker
    fi
done
