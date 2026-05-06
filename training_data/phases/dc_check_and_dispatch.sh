#!/bin/bash
# Damage check hourly: merge shard files, report progress, launch next 5 batches.
# Run from repo root: /home/aomukai/Ninereeds

set -e
cd /home/aomukai/Ninereeds

FILELIST="training_data/phases/damage_check_filelist.txt"
PROGRESS="training_data/phases/damage_check_progress.txt"
DAMAGE_MAP="training_data/phases/damage_map.txt"
BATCH_SIZE=30
WORKERS=5

TOTAL=$(wc -l < "$FILELIST")
DONE=$(wc -l < "$PROGRESS" 2>/dev/null || echo 0)
PENDING=$((TOTAL - DONE))

echo "=== Damage check status: $(date) ==="
echo "Total: $TOTAL | Done: $DONE | Pending: $PENDING"

# Count currently running opencode workers
RUNNING=$(pgrep opencode 2>/dev/null | wc -l)
echo "opencode workers running: $RUNNING"

# Merge all shard files into damage_map.txt
echo "" >> "$DAMAGE_MAP"
SHARDS=$(ls training_data/phases/damage_map_shard_*.txt 2>/dev/null || true)
if [ -n "$SHARDS" ]; then
    # Count issues across all shards
    ISSUE_COUNT=$(cat training_data/phases/damage_map_shard_*.txt 2>/dev/null | grep -c "^phase_" || echo 0)
    echo "Shards found, total issues logged: $ISSUE_COUNT"
    # Rebuild damage_map.txt from all shards (deduplicated)
    cat training_data/phases/damage_map_shard_*.txt 2>/dev/null | sort -u > "$DAMAGE_MAP"
    echo "damage_map.txt updated: $(wc -l < "$DAMAGE_MAP") lines"
else
    echo "No shard files yet."
fi

# Exit if all done
if [ "$PENDING" -le 0 ]; then
    echo "ALL FILES CHECKED. Queue complete."
    exit 0
fi

# Exit if workers still running (give them time)
if [ "$RUNNING" -ge 1 ]; then
    echo "Workers still running — will check again next hour."
    exit 0
fi

# Launch next round of workers
echo "Launching next $WORKERS workers..."

python3 - << 'PYEOF'
import os, glob, subprocess

FILELIST = "training_data/phases/damage_check_filelist.txt"
PROGRESS = "training_data/phases/damage_check_progress.txt"
BATCH_SIZE = 30

all_entries = open(FILELIST).readlines()
done = set()
try:
    done = set(line.strip() for line in open(PROGRESS) if line.strip())
except FileNotFoundError:
    pass

pending = [e for e in all_entries if e.strip().split("|")[1] not in done]
print(f"Pending files: {len(pending)}")

# Determine next batch number
existing = glob.glob("training_data/phases/damage_map_shard_*.txt")
next_batch_num = len(existing) + 1

PROMPT_TEMPLATE = open("/tmp/dc_prompt_template.txt").read() if os.path.exists("/tmp/dc_prompt_template.txt") else None

# Inline template since we can't easily read it from here
TEMPLATE = '''DAMAGE CHECK — POST-REPAIR VERIFICATION
Batch: {batch_num:03d}
Output shard: training_data/phases/damage_map_shard_{batch_num:03d}.txt
Progress file: training_data/phases/damage_check_progress.txt

CONTEXT
-------
These files were identified as damaged in a prior audit and have since been repaired.
You are verifying that each repair succeeded. The "original issue" column shows what
was wrong BEFORE the repair. You are checking the CURRENT state of each file.
Work from repo root: /home/aomukai/Ninereeds

FILES TO CHECK
--------------
{file_list}

TASK
----
For each file:
1. Check damage_check_progress.txt — if filename is already there, skip it.
2. Locate: training_data/phases/phase_N/filename.md
3. Read and verify against format rules below.
4. PASS: append bare filename to damage_check_progress.txt immediately.
5. FAIL: append to damage_map_shard_{batch_num:03d}.txt, then also to progress file.
   Only broken files go in the shard. Clean files go in progress only.

FORMAT RULES (all phases)
--------------------------
Exactly 4 [user]/[Ninereeds] block pairs.
Each [Ninereeds] block: "This is [word]." opener, 5 body lines, summary line with "and".
Every body line must name the target word. No pronouns. No negation.

Phase 1 [user] template: "what does X look like?" / "where can you find X?" / "what does X do?" / "what does X give?"
Phase 2-6 [user] template: "what does X look like?" / "where does X appear?" / "what does X do?" / "what is X for?"

Categories: [TEMPLATE] [STRUCT] [QUALITY] [GRAMMAR] [POS]
Severity: PATCH (minor) or REGENERATE (structural)

RECEIPT
-------
RECEIPT
-------
Batch: {batch_num:03d}
Shard: training_data/phases/damage_map_shard_{batch_num:03d}.txt
Files processed: [comma-separated list]
Issues found: [count]
Progress file last line: [last line of damage_check_progress.txt]
Status: DONE | BLOCKED
'''

for i in range(5):
    batch = pending[i*BATCH_SIZE:(i+1)*BATCH_SIZE]
    if not batch:
        break
    batch_num = next_batch_num + i
    file_lines = []
    for entry in batch:
        parts = entry.strip().split("|")
        fname, phase, issue = parts[1], parts[2], parts[3]
        file_lines.append(f"  {fname}  [phase {phase}]  original: {issue}")
    prompt = TEMPLATE.format(
        batch_num=batch_num,
        file_list="\n".join(file_lines),
    )
    pfile = f"/tmp/dc_prompt_{batch_num:03d}.txt"
    open(pfile, "w").write(prompt)
    subprocess.Popen(
        f'~/.opencode/bin/opencode run -m openrouter/deepseek/deepseek-v4-flash '
        f'--dangerously-skip-permissions "$(cat {pfile})" '
        f'> /tmp/dc_log_{batch_num:03d}.log 2>&1',
        shell=True
    )
    print(f"Launched batch {batch_num:03d} ({len(batch)} files)")
PYEOF

echo "Dispatch complete."
