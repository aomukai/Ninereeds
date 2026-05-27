#!/usr/bin/env python3
"""
Restructure wiki split from:
  wiki/wiki_N/topic/NNN_concept/EN.md
To:
  wiki/level_N/topic/NNN_concept_EN.md

Also renames wiki_1 → level_1, wiki_2 → level_2, etc.

Usage:
  python3 meta/scripts/restructure_wiki.py [--dry-run]
"""

import argparse
import shutil
from pathlib import Path

WIKI_ROOT = Path("training_data/wiki")
LEVEL_MAP = {
    "wiki_1": "level_1",
    "wiki_2": "level_2",
    "wiki_3": "level_3",
    "wiki_4": "level_4",
}


def restructure(dry_run: bool) -> None:
    moved = 0
    errors = []

    for old_level_name, new_level_name in LEVEL_MAP.items():
        old_level = WIKI_ROOT / old_level_name
        if not old_level.exists():
            print(f"Skipping {old_level_name} — not found")
            continue

        new_level = WIKI_ROOT / new_level_name

        # Collect all EN.md files under this level
        en_files = sorted(old_level.rglob("EN.md"))
        print(f"\n{old_level_name} → {new_level_name}: {len(en_files)} files")

        for en_file in en_files:
            # en_file is: wiki/wiki_N/topic/NNN_concept/EN.md
            concept_dir = en_file.parent      # NNN_concept/
            topic_dir   = concept_dir.parent  # topic/

            concept_name = concept_dir.name   # e.g. 001_head
            topic_name   = topic_dir.name     # e.g. body_parts

            new_filename = f"{concept_name}_EN.md"
            dest_dir  = new_level / topic_name
            dest_file = dest_dir / new_filename

            if dry_run:
                print(f"  {en_file} → {dest_file}")
            else:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(en_file), str(dest_file))
                moved += 1

        if not dry_run:
            # Remove now-empty concept directories and old topic dirs
            for concept_dir in sorted(old_level.rglob("*"), reverse=True):
                if concept_dir.is_dir():
                    try:
                        concept_dir.rmdir()  # only removes if empty
                    except OSError:
                        pass  # not empty — leave it
            # Remove old level dir if now empty
            try:
                old_level.rmdir()
                print(f"  Removed empty {old_level_name}/")
            except OSError:
                remaining = list(old_level.rglob("*"))
                if remaining:
                    errors.append(f"  WARNING: {old_level_name}/ not empty — {len(remaining)} items remain")
                    print(errors[-1])

    if not dry_run:
        print(f"\nMoved {moved} files.")

        # Validate: count _EN.md files in new structure
        total = 0
        for new_level_name in LEVEL_MAP.values():
            level_dir = WIKI_ROOT / new_level_name
            if level_dir.exists():
                count = len(list(level_dir.rglob("*_EN.md")))
                print(f"  {new_level_name}: {count} _EN.md files")
                total += count
        print(f"  Total: {total} _EN.md files")

        if errors:
            print("\nErrors:")
            for e in errors:
                print(e)
        else:
            print("Clean — no leftover directories.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Restructure wiki split files")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would happen without making changes")
    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN — no changes will be made\n")

    restructure(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
