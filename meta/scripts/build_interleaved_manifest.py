#!/usr/bin/env python3
"""
build_interleaved_manifest.py

Generates language-rotation-ordered manifest (.txt) files for corpora where
each language variant is a separate file (grounded_stories, triplet_stories,
reasoning).

Current alphabetical sort in build_training_corpus.py puts DE before EN before
JP before ZH for every concept group.  This script reorders them so that the
EDJC/DJCE/JCED/CEDJ rotation pattern applies across concept groups, matching
the within-file rotation already applied to boolean_stories, philosophy, and
lang_1–5.

  group_idx % 4 == 0  →  EN DE JP ZH  (EDJC)
  group_idx % 4 == 1  →  DE JP ZH EN  (DJCE)
  group_idx % 4 == 2  →  JP ZH EN DE  (JCED)
  group_idx % 4 == 3  →  ZH EN DE JP  (CEDJ)

Output files:
  training/corpus/manifests/grounded_stories.txt
  training/corpus/manifests/triplet_stories.txt
  training/corpus/manifests/reasoning.txt

Use these with build_training_corpus.py --order-file when building corpus blocks
for the next training run.

Usage:
  python3 meta/scripts/build_interleaved_manifest.py [--dry-run]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_DIR = ROOT / "training" / "corpus" / "manifests"

ROTATIONS = [
    ["en", "de", "jp", "zh"],   # EDJC
    ["de", "jp", "zh", "en"],   # DJCE
    ["jp", "zh", "en", "de"],   # JCED
    ["zh", "en", "de", "jp"],   # CEDJ
]

# Canonical language suffix → lang key
# EN files in reasoning have no suffix; recognised below
SUFFIX_MAP = {
    "_EN": "en",
    "_DE": "de",
    "_JP": "jp",
    "_ZH": "zh",
}


def lang_of(stem: str) -> str | None:
    """Return lang key for a file stem, or None if not a recognised variant."""
    for suffix, lang in SUFFIX_MAP.items():
        if stem.endswith(suffix):
            return lang
    return None


def base_of(stem: str) -> str:
    """Strip language suffix to get the concept base name."""
    for suffix in SUFFIX_MAP:
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


# ---------------------------------------------------------------------------
# Corpus processors
# ---------------------------------------------------------------------------

def collect_grounded_stories(data_dir: Path) -> list[list[Path]]:
    """Group grounded_stories files by story number.

    Files: story_NN_EN.md, story_NN_DE.md, story_NN_JP.md, story_NN_ZH.md
    Returned: list of groups, each group = [EN, DE, JP, ZH] path (in LANG_ORDER)
    """
    pattern = re.compile(r"^story_(\d+)_(EN|DE|JP|ZH)\.md$")
    groups: dict[int, dict[str, Path]] = {}
    for f in data_dir.rglob("story_*.md"):
        m = pattern.match(f.name)
        if not m:
            continue
        idx, lang = int(m.group(1)), m.group(2).lower()
        groups.setdefault(idx, {})[lang] = f

    result = []
    for idx in sorted(groups):
        g = groups[idx]
        if set(g) == {"en", "de", "jp", "zh"}:
            result.append([g["en"], g["de"], g["jp"], g["zh"]])
        else:
            missing = {"en", "de", "jp", "zh"} - set(g)
            print(f"  [warn] story {idx:03d} missing languages: {missing}")
    return result


def collect_triplet_stories(data_dir: Path) -> list[list[Path]]:
    """Group triplet_stories files by (tier, category, number).

    Files: tier_N/category/category_NN_EN.md, _DE.md, _JP.md, _ZH.md
    Returned: flat list of groups (all tiers combined), each = [EN, DE, JP, ZH]
    """
    groups: dict[str, dict[str, Path]] = {}
    for f in data_dir.rglob("*.md"):
        stem = f.stem
        lang = lang_of(stem)
        if lang is None:
            continue
        # Use the full path relative to data_dir (minus filename) + base to avoid
        # tier/category collisions (e.g. tier_1/animals_nature/ vs tier_4/animals_nature/)
        rel_dir = f.parent.relative_to(data_dir)
        base = str(rel_dir / base_of(stem))
        groups.setdefault(base, {})[lang] = f

    result = []
    for base in sorted(groups):
        g = groups[base]
        if set(g) == {"en", "de", "jp", "zh"}:
            result.append([g["en"], g["de"], g["jp"], g["zh"]])
        else:
            missing = {"en", "de", "jp", "zh"} - set(g)
            print(f"  [warn] {base} missing languages: {missing}")
    return result


def collect_reasoning(data_dir: Path) -> list[list[Path]]:
    """Group reasoning files by concept.

    Files:  concept.md (EN, no suffix), concept_DE.md, concept_JP.md, concept_ZH.md
    Returned: list of groups, each = [EN, DE, JP, ZH]
    """
    # Build map: base_name → {lang: path}
    groups: dict[str, dict[str, Path]] = {}
    for f in sorted(data_dir.glob("*.md")):
        stem = f.stem
        lang = lang_of(stem)
        if lang is not None:
            base = base_of(stem)
        else:
            # EN file with no suffix — only if a sibling _DE file exists
            lang = "en"
            base = stem
        groups.setdefault(base, {})[lang] = f

    # Only include groups with all 4 languages
    result = []
    for base in sorted(groups):
        g = groups[base]
        if set(g) == {"en", "de", "jp", "zh"}:
            result.append([g["en"], g["de"], g["jp"], g["zh"]])
        elif "en" in g and len(g) == 1:
            pass  # EN-only file (no variants) — skip silently
        else:
            missing = {"en", "de", "jp", "zh"} - set(g)
            if missing != {"en", "de", "jp", "zh"}:  # skip totally absent groups
                print(f"  [warn] {base} missing languages: {missing}")
    return result


# ---------------------------------------------------------------------------
# Manifest writer
# ---------------------------------------------------------------------------

def write_manifest(groups: list[list[Path]], output: Path, dry_run: bool) -> None:
    lines: list[str] = []
    for group_idx, group_paths in enumerate(groups):
        target = ROTATIONS[group_idx % 4]
        # group_paths = [EN, DE, JP, ZH] — reorder to target
        lang_to_path = {
            "en": group_paths[0],
            "de": group_paths[1],
            "jp": group_paths[2],
            "zh": group_paths[3],
        }
        for lang in target:
            lines.append(str(lang_to_path[lang].relative_to(ROOT)))

    content = "\n".join(lines) + "\n"
    total_files = len(lines)
    total_groups = len(groups)

    print(f"  {output.relative_to(ROOT)}")
    print(f"  {total_groups} groups × 4 = {total_files} files")
    if not dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        print(f"  Written.")
    else:
        print(f"  [dry-run] not written")
        # Preview first 12 lines
        for line in lines[:12]:
            print(f"    {line}")
        if len(lines) > 12:
            print(f"    ... ({len(lines) - 12} more)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

JOBS = [
    (
        "grounded_stories",
        ROOT / "training_data/02_thinking/grounded_stories",
        collect_grounded_stories,
        MANIFEST_DIR / "grounded_stories.txt",
    ),
    (
        "triplet_stories",
        ROOT / "training_data/01_language/triplet_stories",
        collect_triplet_stories,
        MANIFEST_DIR / "triplet_stories.txt",
    ),
    (
        "reasoning",
        ROOT / "training_data/02_thinking/reasoning",
        collect_reasoning,
        MANIFEST_DIR / "reasoning.txt",
    ),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("corpus", nargs="?", default="all",
                        choices=["all", "grounded_stories", "triplet_stories", "reasoning"])
    args = parser.parse_args()

    jobs = [j for j in JOBS if args.corpus == "all" or j[0] == args.corpus]

    for name, data_dir, collector, output in jobs:
        print(f"\n{'='*50}")
        print(f"  {name}")
        print(f"{'='*50}")
        if not data_dir.exists():
            print(f"  [missing] {data_dir.relative_to(ROOT)}")
            continue
        groups = collector(data_dir)
        write_manifest(groups, output, args.dry_run)

    print()


if __name__ == "__main__":
    main()
