"""
Assemble verified wiki entries into category files.
Reads from tmp/wiki_output/*.md
Uses tmp/wiki_classification.txt (word | level | category) to route each entry.
Writes to:
  training_data/wiki/wiki_1/<category>_entries.md  (L1)
  training_data/wiki/wiki_2/<category>_level2.md   (L2)
  training_data/wiki/wiki_3/<category>_level3.md   (L3)
Idempotent: skips entries whose [user] line is already present in the target file.
"""

import os
import re
import sys

REPO = "/home/aomukai/Ninereeds"
WIKI_OUT_DIR = f"{REPO}/tmp/wiki_output"
CLASSIFICATION = f"{REPO}/tmp/wiki_classification.txt"
VIOLATIONS = f"{REPO}/tmp/wiki_violations.txt"

WIKI_DIRS = {
    "L1": f"{REPO}/training_data/wiki/wiki_1",
    "L2": f"{REPO}/training_data/wiki/wiki_2",
    "L3": f"{REPO}/training_data/wiki/wiki_3",
}

DRY_RUN = "--dry-run" in sys.argv


def load_classification():
    mapping = {}
    with open(CLASSIFICATION) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 3:
                continue
            word, level, category = parts
            safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", word)
            mapping[safe_name] = (word, level, category)
    return mapping


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
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        content = f.read()
    return set(re.findall(r'\[user\][^\n]+', content))


def target_file(level, category):
    base = WIKI_DIRS[level]
    if level == "L1":
        return os.path.join(base, f"{category}_entries.md")
    elif level == "L2":
        return os.path.join(base, f"{category}_level2.md")
    elif level == "L3":
        return os.path.join(base, f"{category}_level3.md")


def read_entry_block(path):
    with open(path) as f:
        content = f.read().strip()
    match = re.search(r"(\[user\].*)", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content


def level_header(level, category):
    name = category.replace("_", " ").title()
    if level == "L1":
        return f"# {name} Entries\n\n"
    elif level == "L2":
        return f"# {name} — Level 2\n\n"
    elif level == "L3":
        return f"# {name} — Level 3\n\n"
    return f"# {name}\n\n"


def main():
    classification = load_classification()
    failed = get_failed_files()
    if failed:
        print(f"Skipping {len(failed)} failed files.")

    if not os.path.isdir(WIKI_OUT_DIR):
        print(f"Output directory not found: {WIKI_OUT_DIR}")
        return

    files = sorted(f for f in os.listdir(WIKI_OUT_DIR) if f.endswith(".md"))

    by_target = {}
    skipped = 0
    unrecognized = 0

    for fname in files:
        safe_name = fname[:-3]  # strip .md
        if fname in failed:
            skipped += 1
            continue
        if safe_name not in classification:
            print(f"  WARNING: {fname} not in classification, skipping")
            unrecognized += 1
            continue
        word, level, category = classification[safe_name]
        if level not in WIKI_DIRS:
            print(f"  WARNING: unknown level {level!r} for {word}, skipping")
            continue
        path = os.path.join(WIKI_OUT_DIR, fname)
        block = read_entry_block(path)
        if not block:
            print(f"  WARNING: no entry block found in {fname}, skipping")
            continue
        target = target_file(level, category)
        by_target.setdefault(target, []).append((word, level, category, block))

    total_entries = sum(len(v) for v in by_target.values())
    print(f"\nAssembling {total_entries} entries into {len(by_target)} category files.")
    if skipped:
        print(f"Skipped {skipped} entries (failed verification).")
    if unrecognized:
        print(f"Skipped {unrecognized} unrecognized files.")

    for target in sorted(by_target.keys()):
        entries = by_target[target]
        level = entries[0][1]
        category = entries[0][2]

        print(f"\n  {os.path.basename(target)}: {len(entries)} entries")
        if DRY_RUN:
            for word, _, _, _ in entries:
                print(f"    + {word}")
            continue

        os.makedirs(os.path.dirname(target), exist_ok=True)
        existing_user_lines = get_existing_user_lines(target)

        deduped = []
        for word, lv, cat, block in entries:
            user_line = re.search(r'\[user\][^\n]+', block)
            if user_line and user_line.group(0) in existing_user_lines:
                print(f"    ~ {word} (already present, skipping)")
                continue
            deduped.append((word, block))

        if not deduped:
            print(f"    (all entries already present)")
            continue

        blocks_to_add = "\n\n".join(block for _, block in deduped)

        if os.path.exists(target):
            with open(target) as f:
                existing = f.read().rstrip()
            new_content = existing + "\n\n" + blocks_to_add + "\n"
        else:
            header = level_header(level, category)
            new_content = header + blocks_to_add + "\n"

        with open(target, "w") as f:
            f.write(new_content)

        for word, _ in deduped:
            print(f"    + {word}")

    if DRY_RUN:
        print("\n(dry run — nothing written)")
    else:
        print(f"\nDone.")


if __name__ == "__main__":
    main()
