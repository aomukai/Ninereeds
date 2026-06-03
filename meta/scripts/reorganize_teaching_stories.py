#!/usr/bin/env python3
"""
reorganize_teaching_stories.py

Reorganizes training_data/teaching_stories/ from a flat folder into:
    teaching_stories/tier_N/domain_name/filename.md

Uses:
  - tmp/story_gen_tracker.jsonl  → filename → (tier, anchor)
  - tmp/phase_vocab.jsonl        → anchor   → domain

Run from the Ninereeds root directory (D:\\Ninereeds):
    python3 meta/scripts/reorganize_teaching_stories.py

Flags:
  --dry-run   Print planned moves without doing anything
  --execute   Actually move the files
"""

import argparse
import json
import shutil
from collections import defaultdict
from pathlib import Path

ROOT         = Path(__file__).resolve().parent.parent.parent
TRACKER_FILE = ROOT / "tmp" / "story_gen_tracker.jsonl"
VOCAB_FILE   = ROOT / "tmp" / "phase_vocab.jsonl"
STORIES_DIR  = ROOT / "training_data" / "teaching_stories"

FALLBACK_DOMAIN = "misc"


def load_anchor_to_domain(vocab_path: Path) -> dict[str, str]:
    """Map anchor label → first domain (lowercased, safe for folder name)."""
    mapping = {}
    for line in vocab_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        label = rec.get("label", "").strip()
        domains = rec.get("domains", [])
        if label and domains:
            mapping[label] = domains[0]
    return mapping


def load_tracker(tracker_path: Path) -> dict[str, dict]:
    """Map filename stem → {tier, anchor} from tracker."""
    mapping = {}
    for line in tracker_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        file_path = rec.get("file", "")
        if not file_path:
            continue
        # tracker stores relative path like "training_data/teaching_stories/able.md"
        filename = Path(file_path).name
        stem = Path(filename).stem
        mapping[stem] = {
            "tier":   rec.get("tier", 0),
            "anchor": rec.get("anchor", ""),
            "file":   filename,
        }
    return mapping


def safe_folder_name(domain: str) -> str:
    return domain.lower().replace(" ", "_").replace("/", "_").replace("-", "_")


def main():
    ap = argparse.ArgumentParser(description="Reorganize teaching_stories into tier/domain folders.")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run",  action="store_true", help="Show planned moves, don't move anything")
    group.add_argument("--execute",  action="store_true", help="Actually move files")
    args = ap.parse_args()

    print(f"ROOT:         {ROOT}")
    print(f"STORIES_DIR:  {STORIES_DIR}")
    print(f"TRACKER:      {TRACKER_FILE}")
    print(f"VOCAB:        {VOCAB_FILE}")
    print()

    anchor_to_domain = load_anchor_to_domain(VOCAB_FILE)
    tracker          = load_tracker(TRACKER_FILE)

    print(f"Vocab entries:   {len(anchor_to_domain)}")
    print(f"Tracker entries: {len(tracker)}")
    print()

    # Find all .md files currently in the flat stories dir (not in subdirs)
    flat_files = [f for f in STORIES_DIR.glob("*.md")]
    print(f"Flat .md files found: {len(flat_files)}")
    print()

    moves        = []   # (src, dst)
    missing_info = []   # files not in tracker
    no_domain    = []   # anchors not in vocab

    for src in sorted(flat_files):
        stem = src.stem
        if stem not in tracker:
            missing_info.append(src.name)
            continue

        info   = tracker[stem]
        tier   = info["tier"]
        anchor = info["anchor"]

        domain = anchor_to_domain.get(anchor)
        if domain is None:
            no_domain.append((src.name, anchor))
            domain = FALLBACK_DOMAIN

        folder = safe_folder_name(domain)
        dst_dir = STORIES_DIR / f"tier_{tier}" / folder
        dst     = dst_dir / src.name
        moves.append((src, dst, tier, folder))

    # Summary
    tier_counts = defaultdict(int)
    domain_counts = defaultdict(int)
    for _, _, tier, domain in moves:
        tier_counts[tier] += 1
        domain_counts[domain] += 1

    print("=== Planned moves by tier ===")
    for t in sorted(tier_counts):
        print(f"  tier_{t}: {tier_counts[t]} files")
    print()

    print("=== Planned moves by domain (top 20) ===")
    for d, count in sorted(domain_counts.items(), key=lambda x: -x[1])[:20]:
        print(f"  {count:4d}  {d}")
    print()

    if missing_info:
        print(f"=== WARNING: {len(missing_info)} files not found in tracker ===")
        for name in missing_info[:10]:
            print(f"  {name}")
        if len(missing_info) > 10:
            print(f"  ... and {len(missing_info) - 10} more")
        print()

    if no_domain:
        print(f"=== WARNING: {len(no_domain)} anchors not found in vocab (→ {FALLBACK_DOMAIN}/) ===")
        for name, anchor in no_domain[:10]:
            print(f"  {name}  (anchor: {anchor!r})")
        if len(no_domain) > 10:
            print(f"  ... and {len(no_domain) - 10} more")
        print()

    print(f"Total moves planned: {len(moves)}")
    print()

    if args.dry_run:
        print("DRY RUN — no files moved.")
        print("First 10 planned moves:")
        for src, dst, tier, domain in moves[:10]:
            print(f"  {src.name}  →  tier_{tier}/{domain}/")
        return

    # Execute
    print("Executing moves...")
    moved = 0
    errors = 0
    for src, dst, tier, domain in moves:
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            moved += 1
        except Exception as e:
            print(f"  ERROR moving {src.name}: {e}")
            errors += 1

    print(f"Done. Moved: {moved}  Errors: {errors}")


if __name__ == "__main__":
    main()
