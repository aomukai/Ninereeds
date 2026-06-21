#!/usr/bin/env bash
# angle_gen_monitor.sh — check progress every 30 min, restart dead workers.
# Run once: bash meta/scripts/angle_gen_monitor.sh &

REPO="/media/aomukai/SSD External/Ninereeds"
LOG="$REPO/tmp/angle_gen_monitor.log"
ENV="$REPO/.env"
SCRIPT="$REPO/meta/scripts/angle_gen.py"
TOTAL=5156

mkdir -p "$REPO/tmp"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"
}

is_running() {
    pgrep -f "angle_gen.py gen --source $1" > /dev/null 2>&1
}

restart_source() {
    local src=$1 workers=$2
    log "RESTART: $src (workers=$workers)"
    (cd "$REPO" && set -a && source "$ENV" && set +a \
        && python3 "$SCRIPT" gen --source "$src" --workers "$workers") &
    log "RESTART: $src launched (PID $!)"
}

log "Monitor started. Checking every 30 minutes."

while true; do
    sleep 1800

    log "=== check ==="
    cd "$REPO" && python3 "$SCRIPT" report 2>&1 | tee -a "$LOG"

    done_count=$(wc -l < "$REPO/training_data/redesign/words_done.txt" 2>/dev/null || echo 0)
    if [ "$done_count" -ge "$TOTAL" ]; then
        log "All $TOTAL words complete. Monitor exiting."
        break
    fi

    for src in deepseek openrouter nvidia; do
        workers=4; [ "$src" = "nvidia" ] && workers=1
        if is_running "$src"; then
            log "OK: $src running"
        else
            log "DEAD: $src — restarting"
            restart_source "$src" "$workers"
        fi
    done
done
