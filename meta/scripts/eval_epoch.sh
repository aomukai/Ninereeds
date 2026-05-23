#!/bin/bash
# eval_epoch.sh — run probe + eval on a checkpoint and append to a report file.
#
# Usage:
#   meta/scripts/eval_epoch.sh <checkpoint_path> <run_label> <report_file>
#
# Example:
#   meta/scripts/eval_epoch.sh core/run_3_interleaved_e1.pt run3_e1 training/logs/run_3_report.md

set -e
PYTHON=/home/aomukai/.unsloth/studio/unsloth_studio/bin/python
CKPT="$1"
LABEL="$2"
REPORT="$3"

if [[ -z "$CKPT" || -z "$LABEL" || -z "$REPORT" ]]; then
  echo "Usage: $0 <checkpoint> <label> <report_file>"
  exit 1
fi

TIMESTAMP=$(date "+%Y-%m-%d %H:%M")

echo "=== $LABEL  ($TIMESTAMP) ==="
echo ""

echo "--- PROBES ---"
$PYTHON meta/scripts/probe.py --checkpoint "$CKPT" --temperature 0.7 --tokens 120

echo ""
echo "--- EVAL ---"
$PYTHON eval.py --checkpoint "$CKPT"
