#!/usr/bin/env python3
"""Generate and launch damage-check batches for post-repair verification."""
import subprocess
import sys
import os

FILELIST = "damage_check_filelist.txt"
PROGRESS = "damage_check_progress.txt"
BATCH_SIZE = 30

PROMPT_TEMPLATE = """\
DAMAGE CHECK — POST-REPAIR VERIFICATION
Batch: {batch_num:03d} (filelist lines {start}-{end} of 1574)
Output shard: training_data/phases/damage_map_shard_{batch_num:03d}.txt
Progress file: training_data/phases/damage_check_progress.txt

CONTEXT
-------
These files were identified as damaged in a prior audit (damage_map_original.txt)
and have since been repaired. You are verifying that each repair succeeded.
The original issue column is for reference only — it tells you what was wrong
BEFORE the repair. You are now checking the CURRENT state of the file.

FILES TO CHECK
--------------
{file_list}

TASK
----
For each file:

1. Check training_data/phases/damage_check_progress.txt. If the filename is
   already listed there, skip it (already verified by a prior run).

2. Locate the file: training_data/phases/phase_N/filename.md
   (e.g., phase_1_958.md → training_data/phases/phase_1/phase_1_958.md)

3. Read the file. Verify it against the format rules below.

4. If the file passes all checks: append the filename (just the bare filename,
   no path) to training_data/phases/damage_check_progress.txt (one per line,
   append-only, do this immediately after verifying, not in a batch at the end).

5. If the file has remaining issues: append one line to
   training_data/phases/damage_map_shard_{batch_num:03d}.txt in this format:
       phase_N_NNN.md PATCH (description) [CATEGORY]
   or
       phase_N_NNN.md REGENERATE (description) [CATEGORY]
   Then ALSO append the filename to the progress file.

   Do NOT write entries for files that pass. Only broken files go in the shard.

FORMAT RULES (all phases)
--------------------------
Every file must have EXACTLY 4 [user]/[Ninereeds] block pairs, separated by
blank lines. No more, no fewer.

Each [user] line is a question about the target word (the word being taught).

Each [Ninereeds] block must:
  - First line: "This is [word]." (exact match — word must match the target)
  - Lines 2-6: five body lines (4 descriptive + 1 summary)
  - Line 7 (the summary): must combine two aspects with "and"
  - Every body line must reference the target word explicitly
  - NO pronouns: he, she, it, they, him, her, his, hers, its, their, theirs,
    we, us, our, ours, I, me, my, mine, you, your, yours
  - No negation in body lines ("not", "never", "doesn't", etc.)
  - No ellipsis, truncation, or placeholder text

PHASE-SPECIFIC QUESTION TEMPLATES
----------------------------------
Phase 1 — the four [user] questions must be exactly:
  1. "what does [word] look like?"
  2. "where can you find [word]?"
  3. "what does [word] do?"
  4. "what does [word] give?"

Phase 2, 3, 4, 5, 6 — the four [user] questions must be exactly:
  1. "what does [word] look like?"
  2. "where does [word] appear?"
  3. "what does [word] do?"
  4. "what is [word] for?"

ISSUE CATEGORIES
----------------
[TEMPLATE] — wrong question template for the phase (e.g., phase 1 using
              "where does X appear?" instead of "where can you find X?")
[STRUCT]   — wrong block count, missing/malformed [user] or [Ninereeds] tags,
              truncated content, placeholder text, missing "This is X." opener
[QUALITY]  — duplicate lines within a block
[GRAMMAR]  — grammatically incorrect sentences
[POS]      — target word used in wrong part of speech (e.g., "Running is fast"
              when the target word "run" should be used as a verb not gerund;
              or a noun used as a verb). Determine the correct POS from context:
              look at the filename wordlist.txt or infer from the word itself.

SEVERITY
--------
PATCH      — minor localised issue (1-2 lines wrong)
REGENERATE — structural issue affecting the whole file or multiple blocks

RECEIPT
-------
End your run with exactly this block:
RECEIPT
-------
Batch: {batch_num:03d}
Shard file: training_data/phases/damage_map_shard_{batch_num:03d}.txt
Files processed this run: [list each filename, comma-separated]
Issues found: [count of files that had remaining issues]
Progress file last entry: [last line of damage_check_progress.txt, read directly]
Status: DONE | IN_PROGRESS | BLOCKED
Blocker (if BLOCKED): [exact reason]
"""


def build_file_list(batch_lines):
    """Format the batch lines into a readable file list for the prompt."""
    lines = []
    for entry in batch_lines:
        parts = entry.strip().split("|")
        idx, fname, phase, issue = parts[0], parts[1], parts[2], parts[3]
        lines.append(f"  {fname} [phase {phase}] — original issue: {issue}")
    return "\n".join(lines)


def get_already_done():
    """Return set of filenames already in the progress file."""
    try:
        with open(PROGRESS) as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()


def get_next_batches(n_batches):
    """Return the next n_batches worth of undone entries from the filelist."""
    all_entries = open(FILELIST).readlines()
    done = get_already_done()
    pending = [e for e in all_entries if e.strip().split("|")[1] not in done]
    print(f"Total entries: {len(all_entries)}, done: {len(done)}, pending: {len(pending)}")
    batches = []
    for i in range(n_batches):
        start = i * BATCH_SIZE
        end = start + BATCH_SIZE
        batch = pending[start:end]
        if not batch:
            break
        batches.append(batch)
    return batches, len(pending)


def launch_batch(batch_num, batch_lines, total_pending):
    """Write prompt to a temp file and launch opencode."""
    # Determine the global line numbers for display
    all_entries = open(FILELIST).readlines()
    done = get_already_done()
    pending_indices = [i+1 for i, e in enumerate(all_entries)
                       if e.strip().split("|")[1] not in done]
    batch_start = pending_indices[0] if pending_indices else 0
    batch_end = pending_indices[min(len(batch_lines)-1, len(pending_indices)-1)] if pending_indices else 0

    file_list_str = build_file_list(batch_lines)
    prompt = PROMPT_TEMPLATE.format(
        batch_num=batch_num,
        start=batch_start,
        end=batch_end,
        file_list=file_list_str,
    )

    prompt_file = f"/tmp/damage_check_batch_{batch_num:03d}.txt"
    with open(prompt_file, "w") as f:
        f.write(prompt)

    cmd = [
        os.path.expanduser("~/.opencode/bin/opencode"), "run",
        "-m", "openrouter/deepseek/deepseek-v4-flash",
        "--dangerously-skip-permissions",
        f"$(cat {prompt_file})"
    ]
    # Use shell=True with heredoc-style so the prompt file is read
    shell_cmd = (
        f"~/.opencode/bin/opencode run "
        f"-m openrouter/deepseek/deepseek-v4-flash "
        f"--dangerously-skip-permissions "
        f'"$(cat {prompt_file})" '
        f"> /tmp/damage_check_batch_{batch_num:03d}.log 2>&1'
    )
    print(f"Launching batch {batch_num:03d} ({len(batch_lines)} files) → "
          f"damage_map_shard_{batch_num:03d}.txt")
    proc = subprocess.Popen(
        f"~/.opencode/bin/opencode run "
        f"-m openrouter/deepseek/deepseek-v4-flash "
        f"--dangerously-skip-permissions "
        f'"$(cat {prompt_file})" '
        f"> /tmp/damage_check_batch_{batch_num:03d}.log 2>&1",
        shell=True
    )
    return proc, batch_num


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    os.chdir(os.path.expanduser("~/Ninereeds"))

    # Determine which batch numbers to use (based on existing shards)
    import glob
    existing_shards = glob.glob("training_data/phases/damage_map_shard_*.txt")
    next_batch_num = len(existing_shards) + 1

    batches, total_pending = get_next_batches(n)
    if not batches:
        print("No pending files — all done!")
        sys.exit(0)

    procs = []
    for i, batch_lines in enumerate(batches):
        batch_num = next_batch_num + i
        proc, bn = launch_batch(batch_num, batch_lines, total_pending)
        procs.append((proc, bn))

    print(f"\nLaunched {len(procs)} workers. Log files: /tmp/damage_check_batch_NNN.log")
    print(f"Pending after this round: {max(0, total_pending - len(batches)*BATCH_SIZE)}")
