#!/usr/bin/env python3
"""
Build the Campaign 14 teaching story order and interleaved training manifest.

Commands:
  stats      - Print domain block statistics (word and file counts)
  manifest   - Write teaching_story_manifest.md + teaching_story_order.json
  interleave - Write campaign14_order.txt (full interleaved file list)

Usage:
  python3 meta/scripts/build_teaching_order.py stats
  python3 meta/scripts/build_teaching_order.py manifest
  python3 meta/scripts/build_teaching_order.py interleave [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "training_data"
CORPUS_ADMIN = ROOT / "training" / "corpus_admin"
TMP = ROOT / "tmp"

VOCAB_FILE = TMP / "phase_vocab.jsonl"
LANG_DIR     = DATA / "01_language"
TEACHING_DIR = LANG_DIR / "teaching_stories"
BOOLEAN_DIR  = LANG_DIR / "boolean_stories"
TRIPLET_DIR  = LANG_DIR / "triplet_stories"
GROUNDED_DIR = DATA / "02_thinking" / "grounded_stories"

# ── Domain → Block assignment ─────────────────────────────────────────────────
# 8 blocks ordered concrete → abstract. Domains from phase_vocab.jsonl.

DOMAIN_BLOCK: dict[str, int] = {
    # Block 1: Concrete/Physical — objects, materials, places, animals, body, colors
    "animals_nature":             1,
    "animals_derived":            1,
    "body_physical_materials":    1,
    "body_parts_actions":         1,
    "body_measure_style":         1,
    "basic_materials_substances": 1,
    "objects_things":             1,
    "places_geography":           1,
    "colors_light_atmosphere":    1,
    "food_cooking":               1,
    "kitchen_food_crafts":        1,
    "domestic_places_services":   1,
    "outdoor_terrain":            1,
    "construction_structural":    1,
    "vehicles_transport":         1,
    "clothing_container":         1,
    "clothing_derived":           1,
    "pressure_container":         1,
    # Block 2: Movement/Actions/Processes
    "movement_physical_actions":  2,
    "actions_care_life":          2,
    "processes_operations":       2,
    "travel_movement":            2,
    "separation_departure":       2,
    "common_verbs":               2,
    "basic_verbs_desire":         2,
    "progression_change":         2,
    "initiation_setup":           2,
    "sound_voice":                2,
    # Block 3: People/Social/Society
    "people_persons":             3,
    "society_institutions":       3,
    "social_people_places":       3,
    "life_social_abstract":       3,
    "medical_health":             3,
    "school_production_cycle":    3,
    "death_sport_direction":      3,
    "misc":                       3,
    "mix_blend":                  3,
    "services_transactions":      3,
    # Block 4: Time
    "time_sequence":              4,
    "time_quantity":              4,
    # Block 5: Emotions (B/D/E target — anchored late after grounding)
    "emotions_feelings":          5,
    # Block 6: Cognitive/Communication
    "basic_cognitive_verbs":      6,
    "communication_reasoning":    6,
    "knowledge_truth":            6,
    "knowledge_abstract":         6,
    "culture_study_media":        6,
    "answer_response":            6,
    # Block 7: Abstract
    "abstract_concepts_info":     7,
    "abstract_properties":        7,
    "abstract_states":            7,
    "visual_abstract_forms":      7,
    "progressive_actions":        7,
    "minimizing_objectives":      7,
    # Block 8: Mathematics
    "math_numbers":               8,
}

DEFAULT_BLOCK = 3  # fallback for unrecognised domains

BLOCK_NAMES = {
    1: "Concrete/Physical",
    2: "Movement/Actions/Processes",
    3: "People/Social/Society",
    4: "Time",
    5: "Emotions",
    6: "Cognitive/Communication",
    7: "Abstract",
    8: "Mathematics",
}

# ── Triplet category → Block ──────────────────────────────────────────────────
# 13 triplet categories mapped to 8 teaching domain blocks.

TRIPLET_BUCKET: dict[str, int] = {
    "animals_and_nature":       1,
    "body_and_health":          1,
    "food_and_meals":           1,
    "home_and_daily_life":      1,
    "weather_and_seasons":      1,
    "tools_and_making":         2,
    "play_and_games":           2,
    "vehicles_and_travel":      2,
    "people_and_relationships": 3,
    "school_and_learning":      6,
    "language_and_grammar":     6,
    "abstract_concepts":        7,
    "math_and_science":         8,
}


# ── Slug helpers ──────────────────────────────────────────────────────────────

def to_slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


# ── Vocab loading ─────────────────────────────────────────────────────────────

def load_vocab() -> dict[str, dict]:
    """Returns {slug: entry} for all vocab entries."""
    entries: dict[str, dict] = {}
    with open(VOCAB_FILE) as f:
        for line in f:
            e = json.loads(line)
            slug = to_slug(e["label"])
            entries[slug] = e
    return entries


def get_block(domains: list[str]) -> int:
    for d in domains:
        if d in DOMAIN_BLOCK:
            return DOMAIN_BLOCK[d]
    return DEFAULT_BLOCK


# ── Teaching story file enumeration ──────────────────────────────────────────

def lookup_vocab(vocab: dict[str, dict], stem: str) -> Optional[dict]:
    """Look up a vocab entry for a file stem, trying hyphen and underscore variants."""
    # Strip variant suffix (_2, _3, etc.)
    base = re.sub(r"_\d+$", "", stem)
    # Try direct lookup, then with hyphens replaced by underscores
    return (vocab.get(base)
            or vocab.get(stem)
            or vocab.get(base.replace("-", "_"))
            or vocab.get(stem.replace("-", "_")))


def get_teaching_files(vocab: dict[str, dict]) -> list[tuple[int, str, str, Path]]:
    """
    Returns list of (block, primary_domain, label, path) for teaching stories.
    Domain is inferred from the bucket directory name (tier_N/bucket/story.md).
    Sorted by (block, domain, tier_num, stem) — tiers in order within each domain.
    """
    raw = []  # (block, domain, tier_num, stem, path)
    for tier_num in range(1, 5):
        tier_dir = TEACHING_DIR / f"tier_{tier_num}"
        if not tier_dir.exists():
            continue
        for bucket_dir in sorted(tier_dir.iterdir()):
            if not bucket_dir.is_dir():
                continue
            domain = bucket_dir.name
            block = DOMAIN_BLOCK.get(domain, DEFAULT_BLOCK)
            for f in sorted(bucket_dir.glob("*.md")):
                raw.append((block, domain, tier_num, f.stem, f))

    raw.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    return [(blk, dom, stem, f) for blk, dom, _tier, stem, f in raw]


def get_boolean_files(vocab: dict[str, dict]) -> list[tuple[int, str, str, Path]]:
    """Returns (block, domain, stem, path) for boolean stories, sorted."""
    results = []
    for f in sorted(BOOLEAN_DIR.glob("bool_*.md")):
        raw_stem = f.stem[len("bool_"):]     # strip bool_ prefix
        entry = lookup_vocab(vocab, raw_stem)
        if entry is None:
            block = DEFAULT_BLOCK
            domain = "unknown"
        else:
            domains = entry.get("domains", [])
            block = get_block(domains)
            domain = domains[0] if domains else "unknown"
        results.append((block, domain, f.stem, f))

    results.sort(key=lambda x: (x[0], x[1], x[2]))
    return results


def get_triplet_files() -> dict[int, list[list[Path]]]:
    """
    Returns {block: [[lang1,lang2,lang3,lang4], ...]} — groups of 4 lang files per story.
    Each group is a single story across all 4 languages.
    Within each block: tiers 1-2 first, then tiers 3-4.
    New structure: triplet_stories/tier_N/category_name/category_NN_LANG.md
    """
    block_stories: dict[int, list[list[Path]]] = defaultdict(list)

    for tier in [1, 2, 3, 4]:
        tier_dir = TRIPLET_DIR / f"tier_{tier}"
        if not tier_dir.exists():
            continue
        for cat_dir in sorted(tier_dir.iterdir()):
            if not cat_dir.is_dir():
                continue
            category = cat_dir.name
            block = TRIPLET_BUCKET.get(category, DEFAULT_BLOCK)
            for f in sorted(cat_dir.glob("*_EN.md")):
                m = re.match(r"^(.+)_(\d+)_EN\.md$", f.name)
                if not m:
                    continue
                num = m.group(2)
                langs = []
                for lang in ["EN", "DE", "JP", "ZH"]:
                    lf = cat_dir / f"{category}_{num}_{lang}.md"
                    if lf.exists():
                        langs.append(lf)
                if langs:
                    block_stories[block].append(langs)

    return dict(block_stories)


def get_grounded_files() -> list[list[Path]]:
    """Returns list of 4-language groups for grounded stories, sorted by story number."""
    groups: dict[int, list[Path]] = defaultdict(list)
    for f in sorted(GROUNDED_DIR.glob("story_*_EN.md")):
        m = re.match(r"^story_(\d+)_EN\.md$", f.name)
        if not m:
            continue
        num = int(m.group(1))
        langs = []
        for lang in ["EN", "DE", "JP", "ZH"]:
            lf = GROUNDED_DIR / f"story_{m.group(1)}_{lang}.md"
            if lf.exists():
                langs.append(lf)
        if langs:
            groups[num] = langs
    return [groups[k] for k in sorted(groups)]


# ── stats command ─────────────────────────────────────────────────────────────

def cmd_stats(args: argparse.Namespace) -> None:
    vocab = load_vocab()
    teaching = get_teaching_files(vocab)
    booleans = get_boolean_files(vocab)
    triplets = get_triplet_files()
    grounded = get_grounded_files()

    print("=== Campaign 14 Teaching Corpus Statistics ===\n")

    teach_by_block: dict[int, list] = defaultdict(list)
    for blk, dom, stem, f in teaching:
        teach_by_block[blk].append((dom, stem))

    bool_by_block: dict[int, int] = defaultdict(int)
    for blk, dom, stem, f in booleans:
        bool_by_block[blk] += 1

    print(f"{'Block':5} {'Name':30} {'Teaching':9} {'Boolean':8} {'Triplet':8}")
    print("-" * 70)
    total_t = total_b = total_trip = 0
    for blk in range(1, 9):
        name = BLOCK_NAMES[blk]
        n_t = len(teach_by_block.get(blk, []))
        n_b = bool_by_block.get(blk, 0)
        trip_groups = triplets.get(blk, [])
        n_trip = sum(len(g) for g in trip_groups)
        print(f"  {blk}    {name:30} {n_t:6} files  {n_b:5} files  {n_trip:5} files")
        total_t += n_t
        total_b += n_b
        total_trip += n_trip

    print("-" * 70)
    grounded_files = sum(len(g) for g in grounded)
    print(f"  Total teaching: {total_t}, boolean: {total_b}, "
          f"triplets: {total_trip}, grounded: {grounded_files}")
    print(f"  Grounded stories: {len(grounded)} stories × 4 langs")

    # Check for stories with no vocab match
    unmatched = [stem for blk, dom, stem, f in teaching if dom == "unknown"]
    if unmatched:
        print(f"\n  WARNING: {len(unmatched)} teaching files with no vocab match:")
        for s in unmatched[:10]:
            print(f"    {s}")
        if len(unmatched) > 10:
            print(f"    ... and {len(unmatched)-10} more")


# ── manifest command ──────────────────────────────────────────────────────────

def cmd_manifest(args: argparse.Namespace) -> None:
    vocab = load_vocab()
    teaching = get_teaching_files(vocab)
    booleans = get_boolean_files(vocab)

    teach_by_block: dict[int, list] = defaultdict(list)
    for blk, dom, stem, f in teaching:
        teach_by_block[blk].append((dom, stem, f))

    bool_by_block: dict[int, list] = defaultdict(list)
    for blk, dom, stem, f in booleans:
        bool_by_block[blk].append((dom, stem, f))

    CORPUS_ADMIN.mkdir(parents=True, exist_ok=True)
    md_path = CORPUS_ADMIN / "teaching_story_manifest.md"
    json_path = CORPUS_ADMIN / "teaching_story_order.json"

    order_records = []

    with open(md_path, "w", encoding="utf-8") as out:
        out.write("# Teaching Story Manifest — Campaign 14\n\n")
        out.write("> Generated by `meta/scripts/build_teaching_order.py manifest`.\n")
        out.write("> Domain order: concrete → action → social → time → emotion → cognitive → abstract → math.\n\n")

        total_t = sum(len(v) for v in teach_by_block.values())
        total_b = sum(len(v) for v in bool_by_block.values())
        out.write(f"**Teaching stories:** {total_t} | **Boolean stories:** {total_b}\n\n")
        out.write("| Block | Name | Teaching | Boolean |\n")
        out.write("|-------|------|----------|----------|\n")
        for blk in range(1, 9):
            out.write(f"| {blk} | {BLOCK_NAMES[blk]} | "
                      f"{len(teach_by_block.get(blk, []))} | "
                      f"{len(bool_by_block.get(blk, []))} |\n")
        out.write("\n## Triplet Bucket Assignments\n\n")
        out.write("Triplet categories mapped to teaching domain blocks for domain-aligned interleaving.\n\n")
        out.write("| Triplet Category | Block | Block Name |\n")
        out.write("|------------------|-------|------------|\n")
        for cat, blk in sorted(TRIPLET_BUCKET.items()):
            out.write(f"| {cat} | {blk} | {BLOCK_NAMES[blk]} |\n")
        out.write("\n---\n")

        for blk in range(1, 9):
            name = BLOCK_NAMES[blk]
            t_entries = teach_by_block.get(blk, [])
            b_entries = bool_by_block.get(blk, [])
            out.write(f"\n## Block {blk} — {name}\n\n")
            out.write(f"Teaching: {len(t_entries)} files | Boolean: {len(b_entries)} files\n\n")

            # Group by domain within block
            by_domain: dict[str, list] = defaultdict(list)
            for dom, stem, f in t_entries:
                by_domain[dom].append((stem, f))

            for dom in sorted(by_domain):
                files_in_domain = by_domain[dom]
                out.write(f"### {dom} ({len(files_in_domain)} files)\n\n")
                for stem, f in files_in_domain:
                    rel = f.relative_to(ROOT)
                    out.write(f"- `{rel}`\n")
                    order_records.append({
                        "block": blk,
                        "block_name": name,
                        "domain": dom,
                        "type": "teaching",
                        "path": str(rel),
                    })
                out.write("\n")

            if b_entries:
                out.write(f"### Boolean stories ({len(b_entries)} files)\n\n")
                for dom, stem, f in b_entries:
                    rel = f.relative_to(ROOT)
                    out.write(f"- `{rel}` ({dom})\n")
                    order_records.append({
                        "block": blk,
                        "block_name": name,
                        "domain": dom,
                        "type": "boolean",
                        "path": str(rel),
                    })
                out.write("\n")

    print(f"Wrote {md_path}")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"entries": order_records}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {json_path}  ({json_path.stat().st_size // 1024} KB)")
    print(f"Total: {len(order_records)} entries")


# ── interleave command ────────────────────────────────────────────────────────

def interleave_block(
    teaching: list[Path],
    booleans: list[Path],
    triplet_groups: list[list[Path]],
    grounded_units: list[list[Path]],
    bool_stride: int,
    triplet_stride: int,
    grounded_stride: int,
) -> list[Path]:
    """
    Interleave teaching + boolean + triplets + grounded for one block.

    Booleans: distributed evenly across all teaching positions so all are used.
    Triplets and grounded: inserted at fixed strides.
    """
    result: list[Path] = []
    triplet_iter = iter(triplet_groups)
    grounded_iter = iter(grounded_units)

    # Compute insertion positions for booleans so all get used evenly
    n_teach = len(teaching)
    n_bool = len(booleans)
    if n_bool > 0 and n_teach > 0:
        # Distribute n_bool insertions across n_teach positions
        bool_positions: set[int] = set()
        for k in range(n_bool):
            pos = int(round((k + 0.5) * n_teach / n_bool))
            bool_positions.add(min(pos, n_teach - 1))
    else:
        bool_positions = set()

    bool_idx = 0
    for i, tf in enumerate(teaching):
        result.append(tf)
        # Insert boolean if this position was selected
        if i in bool_positions and bool_idx < len(booleans):
            result.append(booleans[bool_idx])
            bool_idx += 1
        if (i + 1) % triplet_stride == 0:
            tg = next(triplet_iter, None)
            if tg is not None:
                result.extend(tg)
        if (i + 1) % grounded_stride == 0:
            gg = next(grounded_iter, None)
            if gg is not None:
                result.extend(gg)

    return result


def cmd_interleave(args: argparse.Namespace) -> None:
    # Configurable strides (teaching stories between each insertion)
    bool_stride = getattr(args, "bool_stride", 6)
    triplet_stride = getattr(args, "triplet_stride", 4)
    grounded_stride = getattr(args, "grounded_stride", 26)

    vocab = load_vocab()
    teaching = get_teaching_files(vocab)
    booleans = get_boolean_files(vocab)
    triplet_by_block = get_triplet_files()
    all_grounded = get_grounded_files()

    # Split grounded units evenly across blocks proportional to teaching count
    teach_by_block: dict[int, list[Path]] = defaultdict(list)
    for blk, dom, stem, f in teaching:
        teach_by_block[blk].append(f)

    bool_by_block: dict[int, list[Path]] = defaultdict(list)
    for blk, dom, stem, f in booleans:
        bool_by_block[blk].append(f)

    # Distribute grounded stories proportionally across blocks
    total_teaching = sum(len(v) for v in teach_by_block.values())
    grounded_by_block: dict[int, list[list[Path]]] = defaultdict(list)
    grounded_idx = 0
    for blk in range(1, 9):
        n_teach = len(teach_by_block.get(blk, []))
        n_grounded = round(len(all_grounded) * n_teach / total_teaching)
        end = min(grounded_idx + n_grounded, len(all_grounded))
        grounded_by_block[blk] = all_grounded[grounded_idx:end]
        grounded_idx = end

    # Build full ordered file list
    all_files: list[Path] = []
    block_stats: list[tuple] = []

    for blk in range(1, 9):
        t_files = teach_by_block.get(blk, [])
        b_files = bool_by_block.get(blk, [])
        trip_groups = triplet_by_block.get(blk, [])
        gr_units = grounded_by_block.get(blk, [])

        block_files = interleave_block(
            t_files, b_files, trip_groups, gr_units,
            bool_stride, triplet_stride, grounded_stride,
        )
        n_before = len(all_files)
        all_files.extend(block_files)
        block_stats.append((blk, BLOCK_NAMES[blk], len(t_files), len(block_files)))

    out_path = CORPUS_ADMIN / "campaign14_order.txt"

    print(f"=== Campaign 14 Interleaved Order ===\n")
    print(f"  Strides: boolean=1/{bool_stride}, triplet=1/{triplet_stride}, grounded=1/{grounded_stride}")
    print()
    print(f"{'Block':5} {'Name':30} {'Teaching':10} {'Total files'}")
    print("-" * 65)
    for blk, name, n_t, n_total in block_stats:
        print(f"  {blk}    {name:30} {n_t:8}    {n_total}")
    print("-" * 65)
    print(f"  Grand total: {len(all_files)} files\n")

    if args.dry_run:
        print("[dry-run] Not writing files.")
        return

    CORPUS_ADMIN.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Campaign 14 — Interleaved Training Order\n")
        f.write(f"# Teaching stories (domain-sorted) interleaved with boolean,\n")
        f.write(f"# triplets (domain-aligned), and grounded stories.\n")
        f.write(f"# Strides: bool=1/{bool_stride}, triplet=1/{triplet_stride}, grounded=1/{grounded_stride}\n")
        f.write(f"# Total files: {len(all_files)}\n")
        f.write("#\n")
        cur_blk = None
        blk_map = {v[0]: v for v in block_stats}
        pos_in_block: dict[int, int] = defaultdict(int)
        # Re-generate to annotate block boundaries
        grounded_idx = 0
        all_files_annotated: list[tuple[int, Path]] = []
        for blk in range(1, 9):
            t_files = teach_by_block.get(blk, [])
            b_files = bool_by_block.get(blk, [])
            trip_groups = triplet_by_block.get(blk, [])
            gr_units = grounded_by_block.get(blk, [])
            block_files = interleave_block(
                t_files, b_files, trip_groups, gr_units,
                bool_stride, triplet_stride, grounded_stride,
            )
            for bf in block_files:
                all_files_annotated.append((blk, bf))

        cur_blk = None
        for blk, fpath in all_files_annotated:
            if blk != cur_blk:
                f.write(f"# --- Block {blk}: {BLOCK_NAMES[blk]} ---\n")
                cur_blk = blk
            rel = fpath.relative_to(ROOT)
            f.write(str(rel) + "\n")

    print(f"Wrote {out_path}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Build Campaign 14 teaching story order")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("stats", help="Print domain block statistics")

    sub.add_parser("manifest", help="Write teaching_story_manifest.md and .json")

    p_interleave = sub.add_parser("interleave", help="Write campaign14_order.txt")
    p_interleave.add_argument("--dry-run", action="store_true")
    p_interleave.add_argument("--bool-stride", type=int, default=6,
                               help="Teaching stories between each boolean insertion (default 6)")
    p_interleave.add_argument("--triplet-stride", type=int, default=4,
                               help="Teaching stories between each triplet group (default 4)")
    p_interleave.add_argument("--grounded-stride", type=int, default=26,
                               help="Teaching stories between each grounded story (default 26)")

    args = parser.parse_args()

    if args.cmd == "stats":
        cmd_stats(args)
    elif args.cmd == "manifest":
        cmd_manifest(args)
    elif args.cmd == "interleave":
        cmd_interleave(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
