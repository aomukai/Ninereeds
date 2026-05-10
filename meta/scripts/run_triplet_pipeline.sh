#!/usr/bin/env bash
# Advance the triplet story pipeline one step: rescue missing files, verify,
# assemble, and dispatch the next tier when ready.
# Uses flag files to avoid re-running completed steps.
#
# Exit codes:
#   0 = action taken or state printed (check STATUS: line)
#   1 = error
#
# STATUS output lines (read by the loop):
#   STATUS:T2_RUNNING count=N   — tier 2 still generating, check again soon
#   STATUS:T2_RESCUING count=N  — rescue jobs dispatched for missing tier-2 files
#   STATUS:T3_DISPATCHED        — tier 3 jobs started, check in 1h
#   STATUS:T3_RUNNING count=N   — tier 3 generating
#   STATUS:T4_DISPATCHED        — tier 4 jobs started, check in 1h
#   STATUS:T4_RUNNING count=N   — tier 4 generating
#   STATUS:ALL_DONE             — all 4 tiers assembled

set -euo pipefail

REPO="/home/aomukai/Ninereeds"
SCRIPTS="$REPO/meta/scripts"
TMP="$REPO/tmp"

T2_OUT="$TMP/triplet_t2_output"
T3_OUT="$TMP/triplet_t3_output"
T4_OUT="$TMP/triplet_t4_output"
T2_PROMPTS="$TMP/triplet_t2_prompts"
T3_PROMPTS="$TMP/triplet_t3_prompts"
T4_PROMPTS="$TMP/triplet_t4_prompts"

EXPECTED=141

count_md() {
  local dir="$1"
  if [[ ! -d "$dir" ]]; then echo 0; return 0; fi
  local n
  n=$(ls "$dir"/*.md 2>/dev/null | wc -l) || true
  echo "${n:-0}"
}

rescue_missing() {
  local out_dir="$1"
  local prompt_dir="$2"
  local tier="$3"
  local missing=0

  for prompt_file in "$prompt_dir"/*.txt; do
    local base
    base="$(basename "$prompt_file" .txt)"
    # prompt filename: NNN_anchor.txt → look for NNN_*_anchor.md in output dir
    local num anchor
    num="${base%%_*}"
    anchor="${base#*_}"
    local story_file
    story_file="$(ls "$out_dir"/"${num}"_*_"${anchor}".md 2>/dev/null | head -1 || true)"

    if [[ -z "$story_file" ]]; then
      echo "  Rescuing: $base"
      missing=$((missing + 1))
      "$SCRIPTS/opencode_ds.sh" --json "$prompt_file" \
        > "$TMP/opencode_fanout/${base}_rescue.jsonl" \
        2> "$TMP/opencode_fanout/${base}_rescue.stderr" &
    fi
  done

  if [[ $missing -gt 0 ]]; then
    wait
    echo "  Rescue dispatched $missing jobs for tier $tier. Re-running extraction..."
    python3 - <<'PYEOF'
import os, json, re, glob

REPO = "/home/aomukai/Ninereeds"

for jl in glob.glob(f"{REPO}/tmp/opencode_fanout/*_rescue.jsonl"):
    with open(jl) as f:
        lines = f.readlines()
    for line in lines:
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("type") == "text":
            text = ev.get("text", "") or ev.get("content", "")
            if "[user]" in text and "[Ninereeds]" in text:
                # extract outfile path from the prompt file
                base = os.path.basename(jl).replace("_rescue.jsonl", "")
                # find the prompt file to get the outfile path
                prompt_path = f"{REPO}/tmp/triplet_t2_prompts/{base}.txt"
                for tier_dir in ["t2", "t3", "t4"]:
                    prompt_path = f"{REPO}/tmp/triplet_{tier_dir}_prompts/{base}.txt"
                    if os.path.exists(prompt_path):
                        break
                if os.path.exists(prompt_path):
                    with open(prompt_path) as pf:
                        prompt_text = pf.read()
                    m = re.search(r"Write the finished story to (\S+)", prompt_text)
                    if m:
                        outfile = m.group(1)
                        match = re.search(r"\[user\].*", text, re.DOTALL)
                        if match:
                            os.makedirs(os.path.dirname(outfile), exist_ok=True)
                            with open(outfile, "w") as out:
                                out.write(match.group(0).strip() + "\n")
                            print(f"  Rescued: {outfile}")
PYEOF
  fi
  echo $missing
}

# ─── TIER 2 ───────────────────────────────────────────────────────────────────

t2_count=$(count_md "$T2_OUT")
echo "Tier 2: $t2_count/$EXPECTED files"

if [[ ! -f "$TMP/t2_assembled.flag" ]]; then
  if [[ $t2_count -lt $EXPECTED ]]; then
    echo "STATUS:T2_RUNNING count=$t2_count"
    exit 0
  fi

  echo "Tier 2 generation complete. Verifying..."
  python3 "$SCRIPTS/verify_t2_stories.py"

  echo "Assembling tier 2..."
  python3 "$SCRIPTS/assemble_t2_stories.py"
  touch "$TMP/t2_assembled.flag"
  echo "Tier 2 assembled."
fi

# ─── TIER 3 ───────────────────────────────────────────────────────────────────

t3_count=$(count_md "$T3_OUT")
echo "Tier 3: $t3_count/$EXPECTED files"

if [[ ! -f "$TMP/t3_assembled.flag" ]]; then
  if [[ $t3_count -eq 0 ]]; then
    echo "Generating tier 3 prompts..."
    python3 "$SCRIPTS/generate_t3_prompts.py"
    t3_prompt_count=$(ls "$T3_PROMPTS"/*.txt 2>/dev/null | wc -l || echo 0)
    echo "Dispatching $t3_prompt_count tier-3 jobs..."
    bash "$SCRIPTS/opencode_ds_fanout.sh" --workers 10 "$T3_PROMPTS"/*.txt &
    echo "STATUS:T3_DISPATCHED"
    exit 0
  fi

  if [[ $t3_count -lt $EXPECTED ]]; then
    echo "STATUS:T3_RUNNING count=$t3_count"
    exit 0
  fi

  echo "Tier 3 generation complete. Verifying..."
  python3 "$SCRIPTS/verify_t3_stories.py"

  echo "Assembling tier 3..."
  python3 "$SCRIPTS/assemble_t3_stories.py"
  touch "$TMP/t3_assembled.flag"
  echo "Tier 3 assembled."
fi

# ─── TIER 4 ───────────────────────────────────────────────────────────────────

t4_count=$(count_md "$T4_OUT")
echo "Tier 4: $t4_count/$EXPECTED files"

if [[ ! -f "$TMP/t4_assembled.flag" ]]; then
  if [[ $t4_count -eq 0 ]]; then
    echo "Generating tier 4 prompts..."
    python3 "$SCRIPTS/generate_t4_prompts.py"
    t4_prompt_count=$(ls "$T4_PROMPTS"/*.txt 2>/dev/null | wc -l || echo 0)
    echo "Dispatching $t4_prompt_count tier-4 jobs..."
    bash "$SCRIPTS/opencode_ds_fanout.sh" --workers 10 "$T4_PROMPTS"/*.txt &
    echo "STATUS:T4_DISPATCHED"
    exit 0
  fi

  if [[ $t4_count -lt $EXPECTED ]]; then
    echo "STATUS:T4_RUNNING count=$t4_count"
    exit 0
  fi

  echo "Tier 4 generation complete. Verifying..."
  python3 "$SCRIPTS/verify_t4_stories.py"

  echo "Assembling tier 4..."
  python3 "$SCRIPTS/assemble_t4_stories.py"
  touch "$TMP/t4_assembled.flag"
  echo "Tier 4 assembled."
fi

echo "STATUS:ALL_DONE"
