#!/usr/bin/env python3
"""
Apply the rename map produced by DeepSeek.
Reads tmp/rename_list.txt (original paths) and tmp/rename_map.txt (new paths),
moves files with os.rename(), then stages with git add.

Usage:
    python3 meta/scripts/apply_renames.py [--dry-run]
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LIST_FILE = REPO / "tmp" / "rename_list.txt"
MAP_FILE  = REPO / "tmp" / "rename_map.txt"
PHASES_DIR = REPO / "training_data" / "phases"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    list_lines = LIST_FILE.read_text().splitlines()
    map_lines  = MAP_FILE.read_text().splitlines()

    if len(list_lines) != len(map_lines):
        print(f"ERROR: line count mismatch ({len(list_lines)} vs {len(map_lines)})")
        sys.exit(1)

    pairs = []
    errors = []
    for i, (src_rel, dst_rel) in enumerate(zip(list_lines, map_lines), 1):
        src_rel = src_rel.split("\t")[0].strip()
        dst_rel = dst_rel.strip()

        # Safety: both paths must be under training_data/phases/
        if not src_rel.startswith("training_data/phases/"):
            errors.append(f"line {i}: source outside phases/: {src_rel}")
            continue
        if not dst_rel.startswith("training_data/phases/"):
            errors.append(f"line {i}: target outside phases/: {dst_rel}")
            continue

        src = REPO / src_rel
        dst = REPO / dst_rel

        if not src.exists():
            errors.append(f"line {i}: source missing: {src_rel}")
            continue

        if src == dst:
            continue  # already correct

        pairs.append((src, dst, src_rel, dst_rel))

    if errors:
        print(f"{len(errors)} errors:")
        for e in errors[:20]:
            print(f"  {e}")
        if not args.dry_run:
            sys.exit(1)

    print(f"{len(pairs)} renames {'(dry run)' if args.dry_run else 'to apply'}")

    if args.dry_run:
        for src, dst, sr, dr in pairs[:10]:
            print(f"  {sr} → {dr}")
        if len(pairs) > 10:
            print(f"  ... and {len(pairs)-10} more")
        return

    moved = 0
    failed = []
    for src, dst, sr, dr in pairs:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            os.rename(src, dst)
            moved += 1
        except OSError as e:
            failed.append(f"{sr}: {e}")

    print(f"Moved: {moved}, Failed: {len(failed)}")
    if failed:
        for f in failed[:10]:
            print(f"  {f}")

    # Stage all changes in training_data/phases/
    print("Staging with git...")
    result = subprocess.run(
        ["git", "add", "-A", "training_data/phases/"],
        cwd=REPO, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"git add failed: {result.stderr}")
    else:
        print("Done. Run `git status` to review before committing.")


if __name__ == "__main__":
    main()
