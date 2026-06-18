#!/usr/bin/env python3
"""Build block manifest files for the Campaign 14 thinking block.

Produces three ordered file lists (one per training block):

  c14_02_arithmetic_bridge.txt  — Phase A (c01–c15) then Phase B (p01–p05)
                                    all --no-shuffle; Phase B is conditional
  c14_03_grounded_stories.txt   — story_NN_LANG.md in story-number then language
                                    order; SEQUENTIAL — do NOT shuffle or reorder
  c14_04_reasoning.txt          — reasoning/ files, alphabetical (concept group
                                    then language suffix)

These complement the existing campaign14_blocks/ files (01–08) which cover 01_language.
The full C14 thinking sequence trains as separate train.py invocations:
  1. campaign14_full.txt            (01_language, existing)
  2. c14_02_arithmetic_bridge.txt   (--no-shuffle)
  3. c14_03_grounded_stories.txt    (--no-shuffle)
  4. c14_04_reasoning.txt           (--no-shuffle)

Usage:
  python3 meta/scripts/build_campaign14_thinking_manifests.py [--dry-run] [--verify]
"""

from __future__ import annotations
import argparse, re, sys
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
THINKING    = ROOT / "training_data" / "02_thinking"
BLOCKS_DIR  = ROOT / "training" / "corpus_admin" / "campaign14_blocks"

# Language sort order — keeps all 4 handles of the same story consecutive
LANG_ORDER = {"EN": 0, "DE": 1, "JP": 2, "ZH": 3}


# ── Block builders ─────────────────────────────────────────────────────────────

def block_arithmetic_bridge() -> list[str]:
    """
    Phase A (c01–c15) then Phase B (p01–p05).
    Filename prefix gives correct order; alphabetical sort is sufficient.
    Legacy files (00_bridge_*, 02_counting_*, etc.) are excluded — they live
    in the same directory but belong to earlier experimental passes that are
    superseded by the compact 4-lingual format.
    """
    bridge_dir = THINKING / "arithmetic_bridge"
    paths = []
    for f in sorted(bridge_dir.glob("*.md")):
        stem = f.stem
        if re.match(r"^[cp]\d+_", stem):
            paths.append(str(f.relative_to(ROOT)))
    return paths


def block_grounded_stories() -> list[str]:
    """
    grounded_stories/ ordered by story number then canonical language order
    (EN, DE, JP, ZH). Story number is parsed from the filename: story_NN_LANG.md.
    This preserves the narrative sequence — each story's 4 language versions
    train consecutively so the shared semantic content co-fires in one LR arc.
    """
    gs_dir = THINKING / "grounded_stories"
    raw = []
    for f in gs_dir.glob("*.md"):
        m = re.match(r"^story_(\d+)_([A-Z]+)\.md$", f.name)
        if not m:
            continue
        num  = int(m.group(1))
        lang = m.group(2)
        raw.append((num, LANG_ORDER.get(lang, 99), f))
    raw.sort(key=lambda x: (x[0], x[1]))
    return [str(f.relative_to(ROOT)) for _, _, f in raw]


def block_reasoning() -> list[str]:
    """
    reasoning/ files in alphabetical order.
    Alphabetical groups concept files by name (addition_*, subtraction_*, etc.)
    then language suffix (base=EN, _DE, _JP, _ZH), which is the intended order.
    """
    reasoning_dir = THINKING / "reasoning"
    return [str(f.relative_to(ROOT))
            for f in sorted(reasoning_dir.glob("*.md"))]


# ── Main ───────────────────────────────────────────────────────────────────────

BLOCKS: list[tuple[str, str, callable]] = [
    ("c14_02_arithmetic_bridge", "Arithmetic bridge (Phase A + Phase B)", block_arithmetic_bridge),
    ("c14_03_grounded_stories",  "Grounded stories (sequential)",         block_grounded_stories),
    ("c14_04_reasoning",         "Reasoning (concept groups)",            block_reasoning),
]


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Build Campaign 14 thinking block manifests"
    )
    ap.add_argument("--dry-run", action="store_true",
                    help="print counts without writing files")
    ap.add_argument("--verify", action="store_true",
                    help="check every path exists on disk")
    args = ap.parse_args()

    BLOCKS_DIR.mkdir(parents=True, exist_ok=True)

    missing_total: list[str] = []
    all_paths: list[str] = []

    for slug, label, builder in BLOCKS:
        paths = builder()
        all_paths.extend(paths)

        missing = [p for p in paths if args.verify and not (ROOT / p).exists()]
        missing_total.extend(missing)

        print(f"  {slug}: {len(paths)} files — {label}")
        if missing:
            for m in missing[:5]:
                print(f"    MISSING: {m}")
            if len(missing) > 5:
                print(f"    ... and {len(missing) - 5} more")

        if not args.dry_run:
            out = BLOCKS_DIR / f"{slug}.txt"
            header = f"# Campaign 14 thinking block: {label}\n# {len(paths)} files\n#\n"
            out.write_text(header + "\n".join(paths) + "\n", encoding="utf-8")

    # Combined manifest for reference
    if not args.dry_run:
        combined = ROOT / "training" / "corpus_admin" / "campaign14_thinking_manifest.txt"
        header = (
            "# Campaign 14 — Thinking block manifest\n"
            "# Blocks: arithmetic_bridge (Phase A+B) → grounded_stories → reasoning\n"
            "# Each block trains as a separate train.py invocation with --no-shuffle\n"
            f"# Total: {len(all_paths)} files\n#\n"
        )
        lines = [header]
        for slug, label, builder in BLOCKS:
            block_paths = [p for p in all_paths
                           if any(seg in p for seg in (slug.split("_", 2)[-1],))]
        # Simpler: re-run builders to get per-block paths for the combined file
        lines = [header]
        for slug, label, builder in BLOCKS:
            bpaths = builder()
            lines.append(f"\n# ── {label} ({len(bpaths)} files) {'─'*30}\n")
            lines.extend(p + "\n" for p in bpaths)
        combined.write_text("".join(lines), encoding="utf-8")
        print(f"\nWrote {combined.relative_to(ROOT)}")
        print(f"Wrote {len(BLOCKS)} block files to {BLOCKS_DIR.relative_to(ROOT)}/")

    print(f"\nTotal thinking files: {len(all_paths)}")

    if args.verify:
        if missing_total:
            print(f"\n{len(missing_total)} missing paths — fix before training.")
            sys.exit(1)
        else:
            print(f"All {len(all_paths)} paths verified on disk.")


if __name__ == "__main__":
    main()
