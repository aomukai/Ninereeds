#!/usr/bin/env python3
"""
Sort lang_1 and lang_2 files into domain-bucket subdirectories.

Current structure:  lang_1/word.md,  lang_2/word_N.md  (flat)
Target structure:   lang_1/bucket/word.md,  lang_2/bucket/word_N.md

Domain is looked up from tmp/phase_vocab.jsonl.
19 unmatched stems are hardcoded below.

Usage:
  python3 meta/scripts/sort_lang_by_domain.py --dry-run   # preview only
  python3 meta/scripts/sort_lang_by_domain.py             # execute moves
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LANG_DIR = ROOT / "training_data" / "01_language" / "lang"
VOCAB_FILE = ROOT / "tmp" / "phase_vocab.jsonl"

# Manual classifications for stems not found in phase_vocab.jsonl
MANUAL_DOMAIN: dict[str, str] = {
    "attentioning":                          "basic_cognitive_verbs",
    "blade_of_grass":                        "outdoor_terrain",
    "block_of_wood":                         "basic_materials_substances",
    "brightness":                            "colors_light_atmosphere",
    "click_clack":                           "sound_voice",
    "completeness":                          "abstract_properties",
    "consciousness":                         "basic_cognitive_verbs",
    "crease":                                "objects_things",
    "forgiveness":                           "emotions_feelings",
    "incorrectness":                         "abstract_properties",
    "indefiniteness":                        "abstract_properties",
    "need":                                  "basic_verbs_desire",
    "otherness":                             "abstract_concepts_info",
    "parent_offspring_care_system_design":   "life_social_abstract",
    "politeness":                            "communication_reasoning",
    "rudeness":                              "communication_reasoning",
    "sickness":                              "medical_health",
    "soundness":                             "abstract_properties",
    "tiredness":                             "medical_health",
    "unbounded":                             "abstract_properties",
    "unsoundness":                           "abstract_properties",
    "wellness":                              "medical_health",
}

DEFAULT_DOMAIN = "misc"


def load_vocab() -> dict[str, list[str]]:
    vocab: dict[str, list[str]] = {}
    with open(VOCAB_FILE) as f:
        for line in f:
            e = json.loads(line)
            label = e["label"].lower().replace(" ", "_").replace("-", "_")
            vocab[label] = e.get("domains", [])
    return vocab


def get_domain(stem: str, vocab: dict[str, list[str]]) -> str:
    s = stem.lower().replace("-", "_")
    # Strip all trailing _N suffixes (handles double-suffix like word_3_1)
    base = s
    while True:
        stripped = re.sub(r"_\d+$", "", base)
        if stripped == base:
            break
        base = stripped
    # Manual overrides take priority (some vocab entries have uninformative domains)
    if base in MANUAL_DOMAIN:
        return MANUAL_DOMAIN[base]
    # Vocab lookup
    for key in [base, s, base.replace("_", "-"), s.replace("_", "-")]:
        if key in vocab and vocab[key]:
            return vocab[key][0]
    return DEFAULT_DOMAIN


def sort_lang_dir(lang_path: Path, vocab: dict[str, list[str]], dry_run: bool) -> dict:
    stats: dict[str, int] = defaultdict(int)
    unknown: list[str] = []

    for f in sorted(lang_path.glob("*.md")):
        domain = get_domain(f.stem, vocab)
        if domain == DEFAULT_DOMAIN:
            unknown.append(f.stem)
        dest_dir = lang_path / domain
        dest = dest_dir / f.name
        stats[domain] += 1
        if not dry_run:
            dest_dir.mkdir(exist_ok=True)
            shutil.move(str(f), str(dest))

    return {"stats": dict(stats), "unknown": unknown}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without moving files")
    args = parser.parse_args()

    vocab = load_vocab()

    for level in ["lang_1", "lang_2"]:
        lang_path = LANG_DIR / level
        if not lang_path.exists():
            print(f"Skipping {level} — not found")
            continue

        flat_files = list(lang_path.glob("*.md"))
        if not flat_files:
            print(f"{level}: no flat files found (already sorted?)")
            continue

        print(f"\n{'[DRY RUN] ' if args.dry_run else ''}=== {level} ({len(flat_files)} files) ===")
        result = sort_lang_dir(lang_path, vocab, dry_run=args.dry_run)

        for domain, count in sorted(result["stats"].items(), key=lambda x: -x[1]):
            print(f"  {domain}: {count}")

        if result["unknown"]:
            print(f"  DEFAULT ({DEFAULT_DOMAIN}): {result['unknown']}")

        total = sum(result["stats"].values())
        print(f"  Total: {total}")

    if args.dry_run:
        print("\n[dry-run] No files moved.")
    else:
        print("\nDone.")


if __name__ == "__main__":
    main()
