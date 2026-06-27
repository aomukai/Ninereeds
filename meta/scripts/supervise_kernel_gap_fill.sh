#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

WORDS_FILE="training/corpus_admin/kernel/kernel_gap_words.jsonl"
OUT_ROOT="training_data/kernel_gap_fill"
JSONL_OUT="training/corpus/kernel_gap_fill.jsonl"
JSONL_REPORT="training/corpus/kernel_gap_fill_jsonl_report.md"
LOG_DIR="tmp/kernel_gap_supervisor"
STOP_FILE="$LOG_DIR/STOP"
SLEEP_SECONDS="${SLEEP_SECONDS:-1800}"

mkdir -p "$LOG_DIR" "$OUT_ROOT"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$LOG_DIR/supervisor.log"
}

pid_alive() {
  local pid_file="$1"
  [[ -s "$pid_file" ]] || return 1
  local pid
  pid="$(cat "$pid_file")"
  kill -0 "$pid" 2>/dev/null
}

done_count() {
  [[ -f "$OUT_ROOT/progress/done.txt" ]] && sort -u "$OUT_ROOT/progress/done.txt" | wc -l || printf '0\n'
}

total_count() {
  wc -l < "$WORDS_FILE"
}

start_source() {
  local source="$1"
  local workers="$2"
  local pid_file="$LOG_DIR/${source}.pid"
  local source_log="$LOG_DIR/${source}.log"

  if pid_alive "$pid_file"; then
    log "$source already running as pid $(cat "$pid_file")"
    return
  fi

  rm -f "$pid_file"
  log "starting $source with $workers worker(s)"
  nohup python3 meta/scripts/generate_kernel_corpus.py gen \
    --words-file "$WORDS_FILE" \
    --out-root "$OUT_ROOT" \
    --source "$source" \
    --workers "$workers" \
    --retry-failed \
    >> "$source_log" 2>&1 &
  echo "$!" > "$pid_file"
}

any_provider_alive() {
  pid_alive "$LOG_DIR/openrouter.pid" || pid_alive "$LOG_DIR/deepseek.pid" || pid_alive "$LOG_DIR/nvidia.pid"
}

build_jsonl() {
  log "validating completed gap-fill corpus"
  python3 meta/scripts/generate_kernel_corpus.py validate \
    --words-file "$WORDS_FILE" \
    --out-root "$OUT_ROOT" \
    >> "$LOG_DIR/build.log" 2>&1

  log "building $JSONL_OUT"
  python3 meta/scripts/generate_kernel_corpus.py build-jsonl \
    --words-file "$WORDS_FILE" \
    --out-root "$OUT_ROOT" \
    --output "$JSONL_OUT" \
    --report "$JSONL_REPORT" \
    --lowercase-user-copy \
    >> "$LOG_DIR/build.log" 2>&1
}

log "kernel gap-fill supervisor started"

while true; do
  if [[ -f "$STOP_FILE" ]]; then
    log "stop file present: $STOP_FILE"
    exit 0
  fi

  total="$(total_count)"
  done="$(done_count)"
  log "progress: done=$done total=$total"

  if [[ "$done" -ge "$total" ]]; then
    build_jsonl
    log "gap-fill generation complete"
    exit 0
  fi

  if ! any_provider_alive; then
    log "no active providers; removing stale claims before restart"
    python3 meta/scripts/generate_kernel_corpus.py clean-claims \
      --words-file "$WORDS_FILE" \
      --out-root "$OUT_ROOT" \
      >> "$LOG_DIR/supervisor.log" 2>&1
  fi

  start_source openrouter 3
  start_source deepseek 2
  start_source nvidia 1

  sleep "$SLEEP_SECONDS"
done
