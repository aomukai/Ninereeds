#!/usr/bin/env bash
set -euo pipefail

ROOT="${NINEREEDS_ROOT:-/home/aomukai/Ninereeds}"
CODEX_FUGU="${CODEX_FUGU:-codex-fugu}"

cd "$ROOT"

"$CODEX_FUGU" exec \
  --ephemeral \
  --json \
  -C "$ROOT" \
  'You are the Ninereeds MSM orchestrator. Read training/pipeline/orchestrator_startup.md first, then follow its startup order. Reconstruct state only from repository artifacts, run meta/scripts/msm_orchestrator_status.py, classify the wake reason, and take only the next safe bounded action. If work should be handed to a deterministic runner, write or update the necessary decision/config artifact and state the exact runner command; do not start an open-ended loop. If a sentinel or brake blocks work, stop and report it.' \
  </dev/null
