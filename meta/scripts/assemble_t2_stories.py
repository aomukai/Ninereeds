"""
Assemble verified tier-2 triplet stories into category files.
Reads from tmp/triplet_t2_output/*.md
Writes to training_data/triplet_stories/tier_2/<category>.md  (APPENDS to existing content)

Usage:
  python3 assemble_t2_stories.py              # assemble all
  python3 assemble_t2_stories.py --dry-run    # show what would be written, don't write
"""

import os
import re
import sys

REPO = "/home/aomukai/Ninereeds"
STORY_DIR = f"{REPO}/tmp/triplet_t2_output"
TIER_DIR = f"{REPO}/training_data/triplet_stories/tier_2"
VIOLATIONS = f"{REPO}/tmp/triplet_t2_violations.txt"

DRY_RUN = "--dry-run" in sys.argv


def get_failed_files():
    failed = set()
    if not os.path.exists(VIOLATIONS):
        return failed
    with open(VIOLATIONS) as f:
        for line in f:
            if line.startswith("FAIL "):
                failed.add(line.split()[1].strip())
    return failed


def get_existing_user_lines(path):
    """Return set of [user] prompt lines already present in target file."""
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        content = f.read()
    return set(re.findall(r'\[user\][^\n]+', content))


def parse_category_from_filename(fname):
    parts = fname.replace(".md", "").split("_")
    if len(parts) < 3:
        return None, None
    category = "_".join(parts[1:-1])
    return category, parts[-1]


def read_story_block(path):
    with open(path) as f:
        content = f.read().strip()
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
        print(f"Skipping {len(failed)} failed files (run verify_t2_stories.py first).")

    files = sorted(f for f in os.listdir(STORY_DIR) if f.endswith(".md"))

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
        target = os.path.join(TIER_DIR, f"{category}.md")
        blocks_to_add = "\n\n".join(block for _, _, block in stories)

        print(f"\n  {category}: {len(stories)} stories → {target}")
        for fname, anchor, _ in stories:
            print(f"    + {anchor}")

        if DRY_RUN:
            continue

        existing_user_lines = get_existing_user_lines(target)
        deduped = []
        for fname2, anchor2, block2 in stories:
            user_line = re.search(r'\[user\][^\n]+', block2)
            if user_line and user_line.group(0) in existing_user_lines:
                print(f"    ~ {anchor2} (already present, skipping)")
                continue
            deduped.append((fname2, anchor2, block2))
        if not deduped:
            print(f"    (all stories already present)")
            continue
        blocks_to_add = "\n\n".join(block for _, _, block in deduped)

        if os.path.exists(target):
            with open(target) as f:
                existing = f.read().rstrip()
            new_content = existing + "\n\n" + blocks_to_add + "\n"
        else:
            header = f"# {category.replace('_', ' ').title()} — Tier 2 Stories\n\n"
            new_content = header + blocks_to_add + "\n"

        with open(target, "w") as f:
            f.write(new_content)

    if DRY_RUN:
        print("\n(dry run — nothing written)")
    else:
        print(f"\nDone. Category files updated in {TIER_DIR}/")


if __name__ == "__main__":
    main()
