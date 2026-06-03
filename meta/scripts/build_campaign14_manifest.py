#!/usr/bin/env python3
"""
Build the complete Campaign 14 training manifest.

Training order (one block per section):
  1. phase_A         — semantic-clustered concrete anchors (1494 units × 4 langs)
  2. phase_B         — agents & social (1148 units × 4 langs)
  3. lang_1 + lang_2 — multilingual vocabulary, domain-sorted by block
  4. bridge          — surface-form pre-loading (100 files)
  5. grammar         — dative/accusative/genitive curriculum (11 modules, 1400 files)
  6. lang_3/4/5      — multilingual grammar & Q&A (615 + 316 + 192 files)
  7. teaching + triplets — domain+tier cycling, interleaved (no boolean, no grounded)
  8. boolean         — contrast/elimination stories (800 files)

Output:
  training/corpus_admin/campaign14_manifest.txt   — complete ordered file list
  training/corpus_admin/campaign14_blocks/        — one .txt per block (for verification)

Usage:
  python3 meta/scripts/build_campaign14_manifest.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LANG_DIR     = ROOT / "training_data" / "01_language"
CORPUS_ADMIN = ROOT / "training" / "corpus_admin"
BLOCKS_DIR   = CORPUS_ADMIN / "campaign14_blocks"
ORDER_DIR    = ROOT / "training" / "training_order"

# ── Path remapping ────────────────────────────────────────────────────────────
# Existing JSONL order files still reference the old training_data/ layout.
# These substitutions fix them on read without touching the JSONL files.

PATH_REMAP = {
    "training_data/phase_A/":   "training_data/01_language/phase_A/",
    "training_data/phase_B/":   "training_data/01_language/phase_B/",
    "training_data/bridge/":    "training_data/01_language/bridge/",
    "training_data/grammar/":   "training_data/01_language/grammar/",
}

def remap(path: str) -> str:
    for old, new in PATH_REMAP.items():
        if path.startswith(old):
            return new + path[len(old):]
    return path


# ── Domain → Block (for lang_1/2 ordering) ───────────────────────────────────
# Must match the DOMAIN_BLOCK dict in build_teaching_order.py.

DOMAIN_BLOCK: dict[str, int] = {
    "animals_nature":1,"animals_derived":1,"body_physical_materials":1,
    "body_parts_actions":1,"body_measure_style":1,"basic_materials_substances":1,
    "objects_things":1,"places_geography":1,"colors_light_atmosphere":1,
    "food_cooking":1,"kitchen_food_crafts":1,"domestic_places_services":1,
    "outdoor_terrain":1,"construction_structural":1,"vehicles_transport":1,
    "clothing_container":1,"clothing_derived":1,"pressure_container":1,
    "movement_physical_actions":2,"actions_care_life":2,"processes_operations":2,
    "travel_movement":2,"separation_departure":2,"common_verbs":2,
    "basic_verbs_desire":2,"progression_change":2,"initiation_setup":2,"sound_voice":2,
    "people_persons":3,"society_institutions":3,"social_people_places":3,
    "life_social_abstract":3,"medical_health":3,"school_production_cycle":3,
    "death_sport_direction":3,"misc":3,"mix_blend":3,"services_transactions":3,
    "time_sequence":4,"time_quantity":4,
    "emotions_feelings":5,
    "basic_cognitive_verbs":6,"communication_reasoning":6,"knowledge_truth":6,
    "knowledge_abstract":6,"culture_study_media":6,"answer_response":6,
    "abstract_concepts_info":7,"abstract_properties":7,"abstract_states":7,
    "visual_abstract_forms":7,"progressive_actions":7,"minimizing_objectives":7,
    "math_numbers":8,
}
DEFAULT_BLOCK = 3

BLOCK_NAMES = {
    1: "Concrete/Physical", 2: "Movement/Actions/Processes",
    3: "People/Social/Society", 4: "Time", 5: "Emotions",
    6: "Cognitive/Communication", 7: "Abstract", 8: "Mathematics",
}

TRIPLET_BUCKET: dict[str, int] = {
    "animals_and_nature":1,"body_and_health":1,"food_and_meals":1,
    "home_and_daily_life":1,"weather_and_seasons":1,
    "tools_and_making":2,"play_and_games":2,"vehicles_and_travel":2,
    "people_and_relationships":3,
    "school_and_learning":6,"language_and_grammar":6,
    "abstract_concepts":7,
    "math_and_science":8,
}


# ── Block builders ────────────────────────────────────────────────────────────

def block_from_jsonl(jsonl_path: Path, tag: str) -> list[str]:
    """Read a JSONL order file, extract file paths, apply path remapping."""
    paths = []
    with open(jsonl_path) as f:
        for line in f:
            unit = json.loads(line)
            for p in unit.get("files", []):
                paths.append(remap(p))
    return paths


def block_lang_1_2() -> list[str]:
    """
    lang_1 + lang_2 files, sorted by domain block then domain name then filename.
    Domain is encoded in the parent directory of each file.
    """
    paths = []
    for level in ["lang_1", "lang_2"]:
        level_dir = LANG_DIR / "lang" / level
        raw = []
        for bucket_dir in sorted(level_dir.iterdir()):
            if not bucket_dir.is_dir():
                continue
            domain = bucket_dir.name
            block  = DOMAIN_BLOCK.get(domain, DEFAULT_BLOCK)
            for f in sorted(bucket_dir.glob("*.md")):
                raw.append((block, domain, f.name, f))
        raw.sort(key=lambda x: (x[0], x[1], x[2]))
        paths += [str(f.relative_to(ROOT)) for _, _, _, f in raw]
    return paths


def block_bridge() -> list[str]:
    """Bridge files in numeric filename order."""
    bridge_dir = LANG_DIR / "bridge"
    return [str(f.relative_to(ROOT))
            for f in sorted(bridge_dir.glob("*.md"))]


def block_grammar() -> list[str]:
    """Grammar files: module directories in numeric order, files sorted within each."""
    grammar_dir = LANG_DIR / "grammar"
    paths = []
    for mod_dir in sorted(grammar_dir.iterdir()):
        if mod_dir.is_dir():
            for f in sorted(mod_dir.glob("*.md")):
                paths.append(str(f.relative_to(ROOT)))
    return paths


def block_lang_3_4_5() -> list[str]:
    """
    lang_3/4/5 in natural filename order.
    Prefix encodes sublevel (3a_, 3b_, 3c_, 3d_; 4a_–4d_; 5a_–5f_),
    so alphabetical sort gives the correct curriculum progression.
    """
    paths = []
    for level in ["lang_3", "lang_4", "lang_5"]:
        level_dir = LANG_DIR / "lang" / level
        for f in sorted(level_dir.glob("*.md")):
            paths.append(str(f.relative_to(ROOT)))
    return paths


def block_teaching_triplets() -> list[str]:
    """
    Teaching stories + triplets interleaved by domain block and tier.
    No boolean, no grounded stories (both come separately).
    Tiers cycle within each domain block: tier_1 then tier_2 then tier_3 then tier_4.
    Triplets interleaved at stride 4 (teaching stories between each triplet group).
    """
    teaching_dir = LANG_DIR / "teaching_stories"
    triplet_dir  = LANG_DIR / "triplet_stories"

    # ── Teaching files: (block, domain, tier, stem, path) ────────────────────
    raw_teach = []
    for tier_num in range(1, 5):
        tier_dir = teaching_dir / f"tier_{tier_num}"
        if not tier_dir.exists():
            continue
        for bucket_dir in sorted(tier_dir.iterdir()):
            if not bucket_dir.is_dir():
                continue
            domain = bucket_dir.name
            block  = DOMAIN_BLOCK.get(domain, DEFAULT_BLOCK)
            for f in sorted(bucket_dir.glob("*.md")):
                raw_teach.append((block, domain, tier_num, f.stem, f))
    raw_teach.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    teach_by_block: dict[int, list[Path]] = defaultdict(list)
    for blk, _dom, _tier, _stem, f in raw_teach:
        teach_by_block[blk].append(f)

    # ── Triplet files: {block: [[lang1,lang2,lang3,lang4], ...]} ─────────────
    trip_by_block: dict[int, list[list[Path]]] = defaultdict(list)
    for tier_num in range(1, 5):
        tier_dir = triplet_dir / f"tier_{tier_num}"
        if not tier_dir.exists():
            continue
        for cat_dir in sorted(tier_dir.iterdir()):
            if not cat_dir.is_dir():
                continue
            category = cat_dir.name
            block    = TRIPLET_BUCKET.get(category, DEFAULT_BLOCK)
            for f in sorted(cat_dir.glob("*_EN.md")):
                import re
                m = re.match(r"^(.+)_(\d+)_EN\.md$", f.name)
                if not m:
                    continue
                num   = m.group(2)
                langs = []
                for lang in ["EN", "DE", "JP", "ZH"]:
                    lf = cat_dir / f"{category}_{num}_{lang}.md"
                    if lf.exists():
                        langs.append(lf)
                if langs:
                    trip_by_block[block].append(langs)

    # ── Interleave: teaching stories with triplets at stride 4 ───────────────
    TRIPLET_STRIDE = 4
    all_files: list[Path] = []
    for blk in range(1, 9):
        t_files    = teach_by_block.get(blk, [])
        trip_groups = trip_by_block.get(blk, [])
        trip_iter  = iter(trip_groups)
        for i, tf in enumerate(t_files):
            all_files.append(tf)
            if (i + 1) % TRIPLET_STRIDE == 0:
                tg = next(trip_iter, None)
                if tg is not None:
                    all_files.extend(tg)
        # Flush remaining triplets at end of block
        for tg in trip_iter:
            all_files.extend(tg)

    return [str(f.relative_to(ROOT)) for f in all_files]


def block_boolean() -> list[str]:
    """Boolean stories in alphabetical order."""
    boolean_dir = LANG_DIR / "boolean_stories"
    return [str(f.relative_to(ROOT))
            for f in sorted(boolean_dir.glob("*.md"))]


# ── Main ──────────────────────────────────────────────────────────────────────

BLOCKS: list[tuple[str, str]] = [
    ("01_phase_A",         "Phase A — concrete anchors"),
    ("02_phase_B",         "Phase B — agents & social"),
    ("03_lang_1_2",        "Lang 1+2 — multilingual vocabulary (domain-sorted)"),
    ("04_bridge",          "Bridge — surface-form pre-loading"),
    ("05_grammar",         "Grammar — dative/accusative/genitive (11 modules)"),
    ("06_lang_3_4_5",      "Lang 3+4+5 — multilingual grammar & Q&A"),
    ("07_teaching",        "Teaching stories + triplets (domain+tier cycling)"),
    ("08_boolean",         "Boolean stories — contrast/elimination"),
]


def build_blocks() -> dict[str, list[str]]:
    return {
        "01_phase_A":    block_from_jsonl(ORDER_DIR / "phase_A_order.jsonl",  "phase_A"),
        "02_phase_B":    block_from_jsonl(ORDER_DIR / "phase_B_order.jsonl",  "phase_B"),
        "03_lang_1_2":   block_lang_1_2(),
        "04_bridge":     block_bridge(),
        "05_grammar":    block_grammar(),
        "06_lang_3_4_5": block_lang_3_4_5(),
        "07_teaching":   block_teaching_triplets(),
        "08_boolean":    block_boolean(),
    }


def verify_paths(blocks: dict[str, list[str]]) -> int:
    """Check all paths exist. Returns count of missing files."""
    missing = 0
    for block_id, paths in blocks.items():
        for p in paths:
            if not (ROOT / p).exists():
                print(f"  MISSING [{block_id}]: {p}")
                missing += 1
    return missing


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Print stats without writing files")
    ap.add_argument("--verify", action="store_true",
                    help="Check all paths exist before writing")
    args = ap.parse_args()

    print("Building Campaign 14 manifest...\n")
    blocks = build_blocks()

    total = 0
    print(f"{'Block':<35} {'Files':>7}")
    print("-" * 44)
    for block_id, label in BLOCKS:
        n = len(blocks[block_id])
        total += n
        print(f"  {label:<33} {n:>7,}")
    print("-" * 44)
    print(f"  {'TOTAL':<33} {total:>7,}\n")

    if args.verify:
        print("Verifying paths...")
        missing = verify_paths(blocks)
        if missing:
            print(f"\n{missing} missing files — aborting.")
            sys.exit(1)
        print("All paths verified.\n")

    if args.dry_run:
        print("[dry-run] No files written.")
        return

    # Write individual block files
    BLOCKS_DIR.mkdir(parents=True, exist_ok=True)
    for block_id, label in BLOCKS:
        block_path = BLOCKS_DIR / f"{block_id}.txt"
        lines = [f"# {label}\n"] + [p + "\n" for p in blocks[block_id]]
        block_path.write_text("".join(lines), encoding="utf-8")
        print(f"  Wrote {block_path.name}  ({len(blocks[block_id]):,} files)")

    # Write master manifest
    manifest_path = CORPUS_ADMIN / "campaign14_manifest.txt"
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("# Campaign 14 — Complete Training Manifest\n")
        f.write("# Order: phase_A → phase_B → lang_1/2 → bridge → grammar → lang_3/4/5\n")
        f.write("#         → teaching+triplets (domain+tier cycling) → boolean\n")
        f.write(f"# Total files: {total:,}\n")
        f.write("# Generated by: meta/scripts/build_campaign14_manifest.py\n#\n")
        for block_id, label in BLOCKS:
            f.write(f"\n# ── {label} ({'─' * max(1, 55 - len(label))})\n")
            for p in blocks[block_id]:
                f.write(p + "\n")

    print(f"\nWrote {manifest_path}  ({total:,} total files)")


if __name__ == "__main__":
    main()
