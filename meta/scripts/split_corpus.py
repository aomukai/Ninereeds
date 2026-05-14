#!/usr/bin/env python3
"""
split_corpus.py - Split triplet stories and philosophy dialogues into individual files.

Usage:
  python3 meta/scripts/split_corpus.py triplet [--dry-run]
  python3 meta/scripts/split_corpus.py philosophy [--dry-run]
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TRIPLET_DIR = ROOT / "training_data" / "triplet_stories"
PHIL_DIR = ROOT / "training_data" / "philosophy"


def split_triplet(dry_run=False):
    total_written = 0
    for tier_dir in sorted(TRIPLET_DIR.iterdir()):
        if not tier_dir.is_dir() or not tier_dir.name.startswith("tier_"):
            continue
        for cat_file in sorted(tier_dir.glob("*.md")):
            if re.search(r'_\d{2}_EN\.md$', cat_file.name):
                continue  # already split
            lines = cat_file.read_text(encoding="utf-8").splitlines()
            stories = []
            i = 0
            while i < len(lines):
                if lines[i].startswith("[user]"):
                    user_line = lines[i]
                    j = i + 1
                    while j < len(lines) and not lines[j].strip():
                        j += 1
                    if j < len(lines) and lines[j].startswith("[Ninereeds]"):
                        stories.append(user_line + "\n" + lines[j] + "\n")
                        i = j + 1
                    else:
                        i += 1
                else:
                    i += 1

            cat_name = cat_file.stem
            print(f"  {tier_dir.name}/{cat_file.name}: {len(stories)} stories")
            for n, content in enumerate(stories, 1):
                out_name = f"{cat_name}_{n:02d}_EN.md"
                if not dry_run:
                    (tier_dir / out_name).write_text(content, encoding="utf-8")
            total_written += len(stories)
            if not dry_run:
                cat_file.unlink()
                print(f"    -> {len(stories)} files written, original removed")

    print(f"\nTotal stories split: {total_written}")


def split_philosophy(dry_run=False):
    total_written = 0
    for cat_file in sorted(PHIL_DIR.glob("ninereeds_dialogues_cat*.md")):
        m = re.search(r'cat(\d+)', cat_file.name)
        if not m:
            print(f"  SKIP {cat_file.name}: cannot parse cat number")
            continue
        cat_n = int(m.group(1))

        text = cat_file.read_text(encoding="utf-8")
        # Split on --- dividers; first block is file header
        raw_blocks = re.split(r'\n---\n', text)
        entries = []
        for block in raw_blocks:
            block = block.strip()
            if not block or '[STATEMENT]' not in block:
                continue
            # Strip the ### Entry N.M header line at top
            block = re.sub(r'^###\s+Entry\s+[\d.]+\s*\n+', '', block).strip()
            entries.append(block)

        print(f"  {cat_file.name}: {len(entries)} entries")
        for n, content in enumerate(entries, 1):
            out_name = f"dialogues_cat{cat_n}_{n:02d}.md"
            if not dry_run:
                (PHIL_DIR / out_name).write_text(content + "\n", encoding="utf-8")
        total_written += len(entries)
        if not dry_run:
            cat_file.unlink()
            print(f"    -> {len(entries)} files written, original removed")

    print(f"\nTotal entries split: {total_written}")


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ("triplet", "philosophy"):
        print("Usage: split_corpus.py [triplet|philosophy] [--dry-run]")
        sys.exit(1)

    cmd = args[0]
    dry_run = "--dry-run" in args

    if dry_run:
        print("(dry run — no files will be written or deleted)\n")

    if cmd == "triplet":
        print("Splitting triplet stories...")
        split_triplet(dry_run)
    elif cmd == "philosophy":
        print("Splitting philosophy dialogues...")
        split_philosophy(dry_run)

    print("Done.")


if __name__ == "__main__":
    main()
