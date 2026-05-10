"""
Assemble verified tier-1 triplet stories into category files.
Reads from tmp/triplet_t1_output/*.md
Writes to training_data/triplet_stories/tier_1/<category>.md  (APPENDS to existing content)

Usage:
  python3 assemble_t1_stories.py              # assemble all
  python3 assemble_t1_stories.py --dry-run    # show what would be written, don't write
"""

import os
import re
import sys

REPO = "/home/aomukai/Ninereeds"
STORY_DIR = f"{REPO}/tmp/triplet_t1_output"
TIER1_DIR = f"{REPO}/training_data/triplet_stories/tier_1"
VIOLATIONS = f"{REPO}/tmp/triplet_t1_violations.txt"

DRY_RUN = "--dry-run" in sys.argv


def get_failed_files():
    """Return set of filenames that failed verification."""
    failed = set()
    if not os.path.exists(VIOLATIONS):
        return failed
    with open(VIOLATIONS) as f:
        for line in f:
            if line.startswith("FAIL "):
                failed.add(line.split()[1].strip())
    return failed


def parse_category_from_filename(fname):
    # Format: NNN_category_anchor.md  (category may contain underscores)
    parts = fname.replace(".md", "").split("_")
    # parts[0] = NNN, last part = anchor, middle = category
    if len(parts) < 3:
        return None, None
    category = "_".join(parts[1:-1])
    return category, parts[-1]


def read_story_block(path):
    """Extract the [user]/[Ninereeds] block from a story file."""
    with open(path) as f:
        content = f.read().strip()
    # Find the block starting with [user]
    match = re.search(r"(\[user\].*)", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content


def main():
    if not os.path.isdir(STORY_DIR):
        print(f"Story directory not found: {STORY_DIR}")
        return

    failed = get_failed_files()
    if failed:
        print(f"Skipping {len(failed)} failed files (run verify_t1_stories.py first).")

    files = sorted(
        f for f in os.listdir(STORY_DIR) if f.endswith(".md")
    )

    by_category = {}
    skipped = 0

    for fname in files:
        if fname in failed:
            skipped += 1
            continue
        path = os.path.join(STORY_DIR, fname)
        category, anchor = parse_category_from_filename(fname)
        if not category:
            print(f"  WARNING: could not parse category from {fname}, skipping")
            continue
        block = read_story_block(path)
        if not block:
            print(f"  WARNING: no story block found in {fname}, skipping")
            continue
        if category not in by_category:
            by_category[category] = []
        by_category[category].append((fname, anchor, block))

    print(f"\nAssembling {sum(len(v) for v in by_category.values())} stories into {len(by_category)} category files.")
    if skipped:
        print(f"Skipped {skipped} stories (failed verification).")

    for category in sorted(by_category.keys()):
        stories = by_category[category]
        target = os.path.join(TIER1_DIR, f"{category}.md")

        blocks_to_add = "\n\n".join(block for _, _, block in stories)
        separator = "\n\n"

        print(f"\n  {category}: {len(stories)} stories → {target}")
        for fname, anchor, _ in stories:
            print(f"    + {anchor}")

        if DRY_RUN:
            continue

        if os.path.exists(target):
            with open(target) as f:
                existing = f.read().rstrip()
            new_content = existing + separator + blocks_to_add + "\n"
        else:
            # New file: add a header
            header = f"# {category.replace('_', ' ').title()} — Tier 1 Stories\n\n"
            new_content = header + blocks_to_add + "\n"

        with open(target, "w") as f:
            f.write(new_content)

    if DRY_RUN:
        print("\n(dry run — nothing written)")
    else:
        print(f"\nDone. Category files updated in {TIER1_DIR}/")


if __name__ == "__main__":
    main()
