#!/usr/bin/env python3
"""
Parse DeepSeek output from backfill prompts and write training files.

Usage:
    python3 parse_backfill_output.py --phase 1 --pos nouns

Reads JSONL files from tmp/opencode_fanout/ that match the phase/pos pattern.
Extracts %%% FILE: ... %%% blocks.
Validates line count.
Writes files to training_data/phases/phase_N/.
Appends to training_data/phases/backfill_progress.txt.
Then runs update_taught_words.sh to refresh taught_words.txt.
"""

import argparse
import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PHASES_DIR = REPO / "training_data" / "phases"
FANOUT_DIR = REPO / "tmp" / "opencode_fanout"
PROGRESS_FILE = PHASES_DIR / "backfill_progress.txt"
UPDATE_TAUGHT = REPO / "meta" / "scripts" / "update_taught_words.sh"

EXPECTED_LINES = {
    ("nouns", 1): 31, ("nouns", 2): 31, ("nouns", 3): 31, ("nouns", 6): 31,
    ("nouns", 4): 6,  ("nouns", 5): 6,
    ("verbs", 1): 31, ("verbs", 2): 31, ("verbs", 3): 31, ("verbs", 4): 31,
    ("verbs", 5): 31, ("verbs", 6): 31,
    ("adjectives", 1): 4, ("adjectives", 2): 4, ("adjectives", 3): 4,
    ("adjectives", 4): 4, ("adjectives", 5): 4, ("adjectives", 6): 4,
}


def extract_text_from_jsonl(path):
    """Extract all text content from an opencode JSONL output file."""
    parts = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "text":
            text = obj.get("part", {}).get("text", "")
            if text:
                parts.append(text)
    return "\n".join(parts)


def parse_file_blocks(text):
    """
    Extract file blocks from DeepSeek output.
    Returns list of (filename, word, content) tuples.
    """
    # Match: %%% FILE: path/phase_N_NNNN.md WORD: the_word %%%
    #        [content lines]
    #        %%% END FILE %%%
    pattern = re.compile(
        r'%%%\s*FILE:\s*(\S+)\s+WORD:\s*(\S+)\s*%%%\s*\n(.*?)%%%\s*END FILE\s*%%%',
        re.DOTALL | re.IGNORECASE
    )
    results = []
    for m in pattern.finditer(text):
        filename = m.group(1).strip()
        word = m.group(2).strip()
        content = m.group(3).strip()
        results.append((filename, word, content))
    return results


def validate_content(content, pos, phase):
    """
    Basic validation of file content.
    Returns (ok, reason).
    """
    lines = content.splitlines()
    # Strip trailing empty lines for count
    while lines and not lines[-1].strip():
        lines.pop()

    expected = EXPECTED_LINES.get((pos, phase))
    if expected and len(lines) != expected:
        return False, f"wrong line count: {len(lines)} (expected {expected})"

    # Check first line starts with [user]
    if not lines[0].startswith("[user]"):
        return False, f"first line doesn't start with [user]: {lines[0][:40]}"

    # Check for pronouns in body (warning only for now)
    body = "\n".join(lines)
    pronoun_hits = re.findall(r'\b(it|its|they|their|he|she|his|her)\b', body, re.IGNORECASE)
    if pronoun_hits:
        return False, f"pronouns found: {set(pronoun_hits)}"

    return True, "ok"


def load_done_words():
    """Return set of words already in progress file."""
    done = set()
    if PROGRESS_FILE.exists():
        for line in PROGRESS_FILE.read_text().splitlines():
            m = re.match(r'^DONE\s+\S+\s+\[(.+)\]', line)
            if m:
                done.add(m.group(1).strip())
    return done


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", type=int, required=True, choices=range(1, 7))
    parser.add_argument("--pos", required=True, choices=["nouns", "verbs", "adjectives"])
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and validate but don't write files")
    args = parser.parse_args()

    phase, pos = args.phase, args.pos
    phase_dir = PHASES_DIR / f"phase_{phase}"
    phase_dir.mkdir(parents=True, exist_ok=True)

    # Find relevant JSONL output files
    pattern = f"phase_{phase}_{pos}_*.jsonl"
    jsonl_files = sorted(FANOUT_DIR.glob(pattern))
    if not jsonl_files:
        # Also try without .jsonl extension (some runs output without it)
        jsonl_files = sorted(FANOUT_DIR.glob(f"phase_{phase}_{pos}_*"))
        jsonl_files = [f for f in jsonl_files if f.is_file()]

    if not jsonl_files:
        print(f"No output files found matching: {FANOUT_DIR}/{pattern}")
        return

    print(f"Found {len(jsonl_files)} output files for phase_{phase} {pos}")

    done_words = load_done_words()
    written = 0
    skipped = 0
    failed = []

    for jf in jsonl_files:
        text = extract_text_from_jsonl(jf)
        if not text.strip():
            print(f"  WARNING: {jf.name} — empty output")
            continue

        blocks = parse_file_blocks(text)
        if not blocks:
            print(f"  WARNING: {jf.name} — no file blocks found")
            # Save raw output for debugging
            debug_file = FANOUT_DIR / (jf.stem + "_raw.txt")
            debug_file.write_text(text)
            print(f"    Raw output saved to {debug_file.name}")
            continue

        for filename, word, content in blocks:
            if word in done_words:
                print(f"  SKIP: {word} (already in progress)")
                skipped += 1
                continue

            ok, reason = validate_content(content, pos, phase)
            if not ok:
                print(f"  FAIL: {filename} [{word}] — {reason}")
                failed.append((filename, word, reason))
                continue

            if not args.dry_run:
                # Write file
                out_path = REPO / "training_data" / "phases" / filename
                out_path.write_text(content + "\n" if not content.endswith("\n") else content)
                # Append to progress
                with PROGRESS_FILE.open("a") as fh:
                    fh.write(f"DONE {filename}  [{word}]\n")
                done_words.add(word)
                written += 1
                print(f"  OK: {filename}  [{word}]")
            else:
                print(f"  DRY-RUN OK: {filename}  [{word}]")
                written += 1

    print(f"\nSummary: {written} written, {skipped} skipped, {len(failed)} failed")
    if failed:
        print("Failed:")
        for fname, word, reason in failed:
            print(f"  {fname} [{word}]: {reason}")

    if written > 0 and not args.dry_run:
        print("\nUpdating taught_words.txt...")
        result = subprocess.run(["bash", str(UPDATE_TAUGHT)], capture_output=True, text=True)
        print(result.stdout.strip())
        if result.returncode != 0:
            print(f"WARNING: update_taught_words.sh failed: {result.stderr}")


if __name__ == "__main__":
    main()
