#!/usr/bin/env python3
"""
Build the C15 training manifest — full retrain with rotated language order.

Same block structure as the C14c winning path, but with EDJC/DJCE/JCED/CEDJ
rotation applied to every corpus that has separate per-language files.

Corpora already rotated in-place on disk (no manifest change needed):
  lang_1–5        internal 4-lang stanzas; rotated by rotate_language_order.py
  boolean_stories internal 4-lang blocks; rotated by rotate_language_order.py

Corpora rotated via manifest ordering (separate-file corpora):
  phase_A         1494 concept groups × [EN,DE,JP,ZH] → rotate per group index
  phase_B         1148 concept groups × [EN,DE,JP,ZH] → rotate per group index
  triplet_stories 1345 story groups   × [EN,DE,JP,ZH] → rotate per group index

Included as-is (no rotation):
  bridge          single-language German case drills (structure, not content)
  grammar         German case modules (single-language)
  teaching_stories internal multilingual (would need separate rotation pass)
  vignettes       already designed with EDJC rotation
  arithmetic      compact drills (Peano-ordered, language-mixed internally)

Extra files (new for C15):
  training_data/01_language/metalang/language.md    — what is a language?
  training_data/01_language/metalang/JP_script.md   — Japanese kana/kanji reference

Block order (all --no-shuffle):
  Block 1 (language core):   phase_A → metalang → phase_B → lang_1/2 →
                              bridge → grammar → lang_3/4/5 →
                              teaching+triplets → boolean
  Block 2 (arith+grounded):  arith_bridge (c01–c15) + grounded_stories (rotated)
  Block 3 (reasoning+arithB): reasoning (rotated) + arith_B (p01–p05)
  Block 4 (vignettes):       vignettes (already rotated)
  Block 5 (education):       CKS education dialogues (same as C14c)

Output:
  training/corpus_admin/campaign15_manifest.txt          — language core manifest
  training/corpus_admin/campaign15_blocks/01_phase_A.txt
  … (one .txt per language-core block for verification)

Usage:
  python3 meta/scripts/build_campaign15_manifest.py [--dry-run] [--verify]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT        = Path(__file__).resolve().parents[2]
LANG_DIR    = ROOT / "training_data" / "01_language"
THINK_DIR   = ROOT / "training_data" / "02_thinking"
CORPUS_ADM  = ROOT / "training" / "corpus_admin"
BLOCKS_DIR  = CORPUS_ADM / "campaign15_blocks"
ORDER_DIR   = ROOT / "training" / "training_order"

# Rotation table (same as rotate_language_order.py)
ROTATIONS = [
    ["en", "de", "jp", "zh"],   # EDJC — no change
    ["de", "jp", "zh", "en"],   # DJCE
    ["jp", "zh", "en", "de"],   # JCED
    ["zh", "en", "de", "jp"],   # CEDJ
]

# ── Path remapping (old JSONL files → new corpus layout) ─────────────────────

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


# ── Language suffix detection ─────────────────────────────────────────────────

def lang_of_path(path: str) -> str:
    """Return 'en', 'de', 'jp', or 'zh' based on filename suffix."""
    stem = Path(path).stem
    if stem.endswith("_DE"):
        return "de"
    if stem.endswith("_JP"):
        return "jp"
    if stem.endswith("_ZH"):
        return "zh"
    return "en"   # no suffix = EN


def rotate_group(files: list[str], group_idx: int) -> list[str]:
    """Rotate a 4-file [EN,DE,JP,ZH] group by group index."""
    by_lang: dict[str, str] = {}
    for f in files:
        by_lang[lang_of_path(f)] = f
    target = ROTATIONS[group_idx % 4]
    return [by_lang[l] for l in target if l in by_lang]


# ── Domain → Block (for lang_1/2 and teaching_stories ordering) ──────────────

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

def block_phase(jsonl_path: Path) -> list[str]:
    """Read phase JSONL, rotate each concept group per group index."""
    paths: list[str] = []
    group_idx = 0
    with open(jsonl_path) as f:
        for line in f:
            unit = json.loads(line)
            files = [remap(p) for p in unit.get("files", [])]
            # Only rotate if this is a 4-language group
            langs = {lang_of_path(fp) for fp in files}
            if langs == {"en", "de", "jp", "zh"}:
                paths.extend(rotate_group(files, group_idx))
            else:
                paths.extend(files)
            group_idx += 1
    return paths


def block_metalang() -> list[str]:
    """Small meta-linguistic dialogues: what is a language? + Japanese kana/kanji."""
    metalang_dir = LANG_DIR / "metalang"
    return [str(f.relative_to(ROOT)) for f in sorted(metalang_dir.glob("*.md"))]


def block_lang_1_2() -> list[str]:
    """
    lang_1 + lang_2 — internal 4-lang stanzas already rotated on disk.
    Domain-sorted by block then domain name then filename (same as C14).
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
    return [str(f.relative_to(ROOT)) for f in sorted(bridge_dir.glob("*.md"))]


def block_grammar() -> list[str]:
    """Grammar files: module directories in numeric order."""
    grammar_dir = LANG_DIR / "grammar"
    paths = []
    for mod_dir in sorted(grammar_dir.iterdir()):
        if mod_dir.is_dir():
            for f in sorted(mod_dir.glob("*.md")):
                paths.append(str(f.relative_to(ROOT)))
    return paths


def block_lang_3_4_5() -> list[str]:
    """lang_3/4/5 — internal 4-lang stanzas already rotated on disk."""
    paths = []
    for level in ["lang_3", "lang_4", "lang_5"]:
        level_dir = LANG_DIR / "lang" / level
        for f in sorted(level_dir.glob("*.md")):
            paths.append(str(f.relative_to(ROOT)))
    return paths


def block_teaching_triplets() -> list[str]:
    """
    Teaching stories + triplets interleaved by domain block and tier.
    Triplet groups rotated per group index (EDJC/DJCE/JCED/CEDJ).
    Teaching stories are internal-multilingual — no per-file rotation needed here.
    """
    teaching_dir = LANG_DIR / "teaching_stories"
    triplet_dir  = LANG_DIR / "triplet_stories"

    # Teaching files: (block, domain, tier, stem, path)
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

    # Triplet files: {block: [[en,de,jp,zh], ...]}
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
                m = re.match(r"^(.+)_(\d+)_EN\.md$", f.name)
                if not m:
                    continue
                num   = m.group(2)
                group = []
                for lang in ["EN", "DE", "JP", "ZH"]:
                    lf = cat_dir / f"{category}_{num}_{lang}.md"
                    if lf.exists():
                        group.append(lf)
                if len(group) == 4:
                    trip_by_block[block].append(group)

    # Interleave: teaching at stride 4, triplets in rotated language order
    TRIPLET_STRIDE = 4
    all_files: list[Path] = []
    trip_group_counter = 0   # global counter across all blocks for rotation index

    for blk in range(1, 9):
        t_files      = teach_by_block.get(blk, [])
        trip_groups  = trip_by_block.get(blk, [])
        trip_iter    = iter(trip_groups)
        for i, tf in enumerate(t_files):
            all_files.append(tf)
            if (i + 1) % TRIPLET_STRIDE == 0:
                tg = next(trip_iter, None)
                if tg is not None:
                    rotated = [tg[{"en":0,"de":1,"jp":2,"zh":3}[l]]
                               for l in ROTATIONS[trip_group_counter % 4]]
                    all_files.extend(rotated)
                    trip_group_counter += 1
        for tg in trip_iter:
            rotated = [tg[{"en":0,"de":1,"jp":2,"zh":3}[l]]
                       for l in ROTATIONS[trip_group_counter % 4]]
            all_files.extend(rotated)
            trip_group_counter += 1

    return [str(f.relative_to(ROOT)) for f in all_files]


def block_boolean() -> list[str]:
    """Boolean stories — already rotated in place; alphabetical sort preserves it."""
    boolean_dir = LANG_DIR / "boolean_stories"
    return [str(f.relative_to(ROOT)) for f in sorted(boolean_dir.glob("*.md"))]


# ── Main ──────────────────────────────────────────────────────────────────────

BLOCKS: list[tuple[str, str]] = [
    ("01_phase_A",    "Phase A — concrete anchors (rotated)"),
    ("02_metalang",   "Metalang — language.md + JP_script.md"),
    ("03_phase_B",    "Phase B — agents & social (rotated)"),
    ("04_lang_1_2",   "Lang 1+2 — multilingual vocabulary (pre-rotated stanzas)"),
    ("05_bridge",     "Bridge — surface-form pre-loading"),
    ("06_grammar",    "Grammar — dative/accusative/genitive"),
    ("07_lang_3_4_5", "Lang 3+4+5 — multilingual grammar & Q&A (pre-rotated)"),
    ("08_teaching",   "Teaching stories + triplets (triplets rotated)"),
    ("09_boolean",    "Boolean stories (pre-rotated)"),
]


def build_blocks() -> dict[str, list[str]]:
    return {
        "01_phase_A":    block_phase(ORDER_DIR / "phase_A_order.jsonl"),
        "02_metalang":   block_metalang(),
        "03_phase_B":    block_phase(ORDER_DIR / "phase_B_order.jsonl"),
        "04_lang_1_2":   block_lang_1_2(),
        "05_bridge":     block_bridge(),
        "06_grammar":    block_grammar(),
        "07_lang_3_4_5": block_lang_3_4_5(),
        "08_teaching":   block_teaching_triplets(),
        "09_boolean":    block_boolean(),
    }


def verify_paths(blocks: dict[str, list[str]]) -> int:
    missing = 0
    for block_id, paths in blocks.items():
        for p in paths:
            if not (ROOT / p).exists():
                print(f"  MISSING [{block_id}]: {p}")
                missing += 1
    return missing


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Don't write files")
    parser.add_argument("--verify",  action="store_true", help="Check all paths exist")
    args = parser.parse_args()

    print("\nBuilding Campaign 15 language core manifest...")
    blocks = build_blocks()

    all_paths: list[str] = []
    for block_id, label in BLOCKS:
        paths = blocks[block_id]
        print(f"  {block_id}  {len(paths):>6} files   {label}")
        all_paths.extend(paths)

    print(f"\n  Total: {len(all_paths):,} files")

    if args.verify:
        missing = verify_paths(blocks)
        if missing:
            print(f"\n  {missing} missing files — fix before training")
            sys.exit(1)
        else:
            print("  All paths verified.")

    if args.dry_run:
        print("  [dry-run] no files written")
        return

    BLOCKS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = CORPUS_ADM / "campaign15_manifest.txt"

    # Write per-block files
    for block_id, label in BLOCKS:
        block_file = BLOCKS_DIR / f"c15_{block_id}.txt"
        block_file.write_text("\n".join(blocks[block_id]) + "\n", encoding="utf-8")

    # Write full manifest
    lines = [
        "# Campaign 15 — Language core manifest (rotated)",
        "# Base: checkpoints/c13_Phase_C_winner.pt",
        "# Block structure: same as C14c winner path but with rotated corpus",
        "# Generated by: meta/scripts/build_campaign15_manifest.py",
        f"# Total files: {len(all_paths):,}",
        "",
    ]
    for block_id, label in BLOCKS:
        lines.append(f"# ── {label}")
        lines.extend(blocks[block_id])
        lines.append("")

    manifest_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  Manifest → {manifest_path.relative_to(ROOT)}")
    print(f"  Blocks   → {BLOCKS_DIR.relative_to(ROOT)}/c15_*.txt")
    print()


if __name__ == "__main__":
    main()
