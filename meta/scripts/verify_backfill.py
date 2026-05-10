#!/usr/bin/env python3
"""
Verify and record the results of a backfill fanout run.

After DeepSeek has written files to disk (via its write tool), this script:
1. Checks which expected files exist
2. Validates format (line count, no pronouns, etc.)
3. Updates backfill_progress.txt for valid files
4. Runs update_taught_words.sh if new files were accepted

Usage:
    python3 verify_backfill.py --phase 1 --pos nouns
"""

import argparse
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VOCAB = REPO / "vocab"
PHASES_DIR = REPO / "training_data" / "phases"
PROMPTS_DIR = REPO / "tmp" / "backfill_prompts"
PROGRESS_FILE = PHASES_DIR / "backfill_progress.txt"
UPDATE_TAUGHT = REPO / "meta" / "scripts" / "update_taught_words.sh"

FILE_NUM_FORMAT = {1: "04d", 2: "03d", 3: "03d", 4: "03d", 5: "04d", 6: "04d"}

EXPECTED_LINES = {
    ("nouns", 1): 31, ("nouns", 2): 31, ("nouns", 3): 31, ("nouns", 6): 31,
    ("nouns", 4): 6,  ("nouns", 5): 6,
    ("verbs", 1): 31, ("verbs", 2): 31, ("verbs", 3): 31, ("verbs", 4): 31,
    ("verbs", 5): 31, ("verbs", 6): 31,
    ("adjectives", 1): 4, ("adjectives", 2): 4, ("adjectives", 3): 4,
    ("adjectives", 4): 4, ("adjectives", 5): 4, ("adjectives", 6): 4,
}


def load_done_words():
    done = set()
    if PROGRESS_FILE.exists():
        for line in PROGRESS_FILE.read_text().splitlines():
            m = re.match(r'^DONE\s+\S+\s+\[(.+)\]', line)
            if m:
                done.add(m.group(1).strip())
    return done


def get_file_map(phase, pos):
    """
    Read prompt files to rebuild the word→filename mapping.
    Returns dict: word → relative_path (e.g. phase_1/phase_1_1250.md)
    """
    file_map = {}
    prompt_pat = re.compile(rf"phase_{phase}_{pos}_\d+\.txt$")
    for pf in sorted(PROMPTS_DIR.glob(f"phase_{phase}_{pos}_*.txt")):
        text = pf.read_text()
        # Match both old format "Word: 'x' → write to: path" and new lean "'x' → path"
        for m in re.finditer(
            r"'(\S+)'\s*→(?:\s*write to:)?\s*training_data/phases/(\S+)",
            text
        ):
            word = m.group(1)
            rel_path = m.group(2).rstrip("'")
            file_map[word] = rel_path
    return file_map


def validate_file(path, pos, phase):
    """Returns (ok, reason)."""
    if not path.exists():
        return False, "file not found"

    content = path.read_text()
    lines = content.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()

    expected = EXPECTED_LINES.get((pos, phase))
    if expected and len(lines) != expected:
        return False, f"wrong line count: {len(lines)} (expected {expected})"

    if not lines:
        return False, "empty file"

    if not lines[0].startswith("[user]"):
        return False, f"first line doesn't start with [user]: {lines[0][:40]}"

    body = "\n".join(lines)
    # Check for "This is" pattern (old wrong format)
    if "[Ninereeds]This is " in body:
        return False, "old 'This is' format found"

    # Warn on pronouns (these files shouldn't have them)
    pronoun_hits = re.findall(r'\b(it|its|they|their)\b', body, re.IGNORECASE)
    if pronoun_hits:
        return False, f"pronouns found: {set(pronoun_hits)}"

    return True, "ok"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", type=int, required=True, choices=range(1, 7))
    parser.add_argument("--pos", required=True, choices=["nouns", "verbs", "adjectives"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    phase, pos = args.phase, args.pos

    file_map = get_file_map(phase, pos)
    if not file_map:
        print(f"No file map found — run generate_backfill_prompts.py first.")
        return

    print(f"Expected files for phase_{phase} {pos}: {len(file_map)}")

    done_words = load_done_words()
    accepted = 0
    missing = []
    failed = []

    for word, rel_path in sorted(file_map.items(), key=lambda x: x[1]):
        if word in done_words:
            print(f"  SKIP: {word} (already done)")
            continue

        full_path = PHASES_DIR / rel_path.replace(f"phase_{phase}/", f"phase_{phase}/")
        # Normalize: rel_path is like "phase_1/phase_1_1250.md"
        full_path = REPO / "training_data" / "phases" / rel_path

        ok, reason = validate_file(full_path, pos, phase)
        if not ok:
            if reason == "file not found":
                missing.append((word, rel_path))
            else:
                failed.append((word, rel_path, reason))
                print(f"  FAIL: {rel_path} [{word}] — {reason}")
            continue

        if not args.dry_run:
            with PROGRESS_FILE.open("a") as fh:
                fh.write(f"DONE {rel_path}  [{word}]\n")
            done_words.add(word)
            accepted += 1
            print(f"  OK: {rel_path}  [{word}]")
        else:
            print(f"  DRY-RUN OK: {rel_path}  [{word}]")
            accepted += 1

    print(f"\nSummary: {accepted} accepted, {len(missing)} missing, {len(failed)} failed")
    if missing:
        print(f"Missing files ({len(missing)}):")
        for word, path in missing[:10]:
            print(f"  {path}  [{word}]")
        if len(missing) > 10:
            print(f"  ... and {len(missing) - 10} more")

    if accepted > 0 and not args.dry_run:
        print("\nUpdating taught_words.txt...")
        result = subprocess.run(["bash", str(UPDATE_TAUGHT)], capture_output=True, text=True)
        print(result.stdout.strip())

    # Print queue status using full queue + full progress
    queue_file = VOCAB / f"phase_{phase}_{pos}_new.txt"
    if queue_file.exists():
        all_words = [l.strip() for l in queue_file.read_text().splitlines() if l.strip()]
        total_queue = len(all_words)
        total_done = len([w for w in all_words if w in done_words])
        print(f"\nQueue: {total_done}/{total_queue} complete, {total_queue - total_done} remaining")


if __name__ == "__main__":
    main()
