#!/usr/bin/env python3
"""
Build the final curriculum training order from inventory/curriculum_graph.json.

Adds two layers on top of the raw dependency graph:

  1. Curriculum tier — manually assigned concreteness priority:
       1 = concrete early domain (animals, body, food, objects, colors)
       2 = concrete extensions (places, movement, outdoor, domestic)
       3 = social / people / actions
       4 = systems / processes / information
       5 = abstract reasoning / math / communication / philosophy

     Tier overrides embedding cluster order; depth remains a hard constraint
     (a depth-1 cluster never trains before its depth-0 prerequisites).

  2. Deduplication — concepts sharing a base name (word, word_2, word_3 …)
     within the same cluster are collapsed to one canonical entry.
     The canonical is the one with the shortest name (no suffix preferred).
     Variant count is noted; all variants are included in the chunk file list.

Outputs:
  training/corpus_admin/curriculum_manifest.md   updated, tier-ordered
  training/corpus_admin/curriculum_order.json    machine-readable order

Usage:
  python meta/scripts/build_curriculum_order.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# ── Tier assignments ──────────────────────────────────────────────────────────
# Edit these to adjust curriculum priority.
# Tier 1 = train earliest; tier 5 = defer until concrete domains are stable.
# Key = cluster ID from curriculum_graph.json ("d{depth}_g{label}").

CLUSTER_TIERS: dict[str, int] = {
    # ── Phase A: Concrete anchors ──────────────────────────────────────────
    # animals, body, food, water, home, places, objects, colors
    "d0_g11": 1,   # Colors / Light / Atmosphere     (p1: 52%)
    "d0_g2":  1,   # Animals / Nature                (p1: 56%)
    "d0_g13": 1,   # Basic Materials / Substances    (p1: 60%) — water, food, cup
    "d0_g5":  1,   # Body / Physical Materials       (p1: 68%)
    "d0_g7":  1,   # Objects / Things                (p1: 50%)
    "d0_g10": 1,   # Places / Geography              — home, city, place
    "d1_g14": 1,   # Animals (derived)               (p1: 85%)
    "d1_g4":  1,   # Food / Cooking                  (p1: 62%)
    "d1_g6":  1,   # Body Parts / Actions            — hands, eyes, feet
    "d1_g9":  1,   # Vehicles / Transport            (p1: 84%)
    "d2_g6":  1,   # Kitchen / Food / Crafts

    # ── Phase B: Concrete relations ────────────────────────────────────────
    # parts, materials, simple actions, tools, movement, locations
    "d0_g14": 2,   # Emotions / Feelings             — sensory/physical states
    "d0_g17": 2,   # Movement / Physical Actions     (p1: 44%)
    "d0_g8":  2,   # Basic Verbs / Desire
    "d0_g9":  2,   # Separation / Departure
    "d1_g10": 2,   # Domestic / Places / Services
    "d1_g12": 2,   # Body Measure / Style            (p1: 48%)
    "d1_g13": 2,   # Construction / Structural
    "d1_g15": 2,   # Outdoor / Terrain
    "d1_g8":  2,   # Travel / Movement
    "d3_g3":  2,   # Clothing / Container            (p1: 75%)
    "d4_g0":  2,   # Clothing (derived)
    "d4_g1":  2,   # Pressure / Container
    "d5_g2":  2,   # Sound / Voice

    # ── Phase C: Agents and social world ───────────────────────────────────
    # people, roles, family, jobs, communication basics
    "d0_g12": 3,   # Society / Institutions
    "d0_g16": 3,   # People / Persons                (deduplicated)
    "d0_g3":  3,   # Actions / Care / Life
    "d0_g4":  3,   # Processes / Operations
    "d1_g11": 3,   # Life / Social / Abstract
    "d1_g2":  3,   # Medical / Health
    "d1_g3":  3,   # Progression / Change
    "d2_g2":  3,   # Common Verbs
    "d2_g3":  3,   # Social / People / Places        — children, girl, human, wife
    "d3_g0":  3,   # Misc (3 concepts)
    "d3_g1":  3,   # Death / Sport / Direction
    "d5_g0":  3,   # Mix / Blend

    # ── Phase D: Processes and systems ────────────────────────────────────
    # growth, change, cause/effect, weather, machines, economy, institutions
    "d0_g6":  4,   # Abstract Concepts / Info
    "d0_g15": 4,   # Basic Cognitive Verbs
    "d0_g18": 4,   # Time / Sequence
    "d1_g0":  4,   # Visual / Abstract Forms
    "d1_g5":  4,   # Knowledge / Truth
    "d1_g7":  4,   # Time / Quantity
    "d2_g4":  4,   # Initiation / Setup
    "d2_g8":  4,   # Services / Transactions
    "d3_g2":  4,   # School / Production / Cycle
    "d5_g1":  4,   # Answer / Response

    # ── Phase E: Abstraction ───────────────────────────────────────────────
    # math, reasoning, uncertainty, ethics, philosophy, consciousness, meta-language
    "d0_g0":  5,   # Math / Numbers                  (p6: 56%)
    "d0_g1":  5,   # Abstract Properties             (p6: 57%)
    "d0_g19": 5,   # Communication / Reasoning       (p6: 68%)
    "d1_g1":  5,   # Culture / Study / Media         (p6: 74%)
    "d2_g0":  5,   # Abstract States                 (p6: 50%)
    "d2_g1":  5,   # Progressive Actions             (p6: 68%)
    "d2_g5":  5,   # Knowledge / Abstract            (p6: 71%)
    "d2_g7":  5,   # Minimizing / Objectives         (p6: 58%)
}

CLUSTER_LABELS: dict[str, str] = {
    "d0_g0":  "Math / Numbers",
    "d0_g1":  "Abstract Properties",
    "d0_g10": "Places / Geography",
    "d0_g11": "Colors / Light / Atmosphere",
    "d0_g12": "Society / Institutions",
    "d0_g13": "Basic Materials / Substances",
    "d0_g14": "Emotions / Feelings",
    "d0_g15": "Basic Cognitive Verbs",
    "d0_g16": "People / Persons",
    "d0_g17": "Movement / Physical Actions",
    "d0_g18": "Time / Sequence",
    "d0_g19": "Communication / Reasoning",
    "d0_g2":  "Animals / Nature",
    "d0_g3":  "Actions / Care / Life",
    "d0_g4":  "Processes / Operations",
    "d0_g5":  "Body / Physical Materials",
    "d0_g6":  "Abstract Concepts / Info",
    "d0_g7":  "Objects / Things",
    "d0_g8":  "Basic Verbs / Desire",
    "d0_g9":  "Separation / Departure",
    "d1_g0":  "Visual / Abstract Forms",
    "d1_g1":  "Culture / Study / Media",
    "d1_g10": "Domestic / Places / Services",
    "d1_g11": "Life / Social / Abstract",
    "d1_g12": "Body Measure / Style",
    "d1_g13": "Construction / Structural",
    "d1_g14": "Animals (derived)",
    "d1_g15": "Outdoor / Terrain",
    "d1_g2":  "Medical / Health",
    "d1_g3":  "Progression / Change",
    "d1_g4":  "Food / Cooking",
    "d1_g5":  "Knowledge / Truth",
    "d1_g6":  "Body Parts / Actions",
    "d1_g7":  "Time / Quantity",
    "d1_g8":  "Travel / Movement",
    "d1_g9":  "Vehicles / Transport",
    "d2_g0":  "Abstract States",
    "d2_g1":  "Progressive Actions",
    "d2_g2":  "Common Verbs",
    "d2_g3":  "Social / People / Places",
    "d2_g4":  "Initiation / Setup",
    "d2_g5":  "Knowledge / Abstract",
    "d2_g6":  "Kitchen / Food / Crafts",
    "d2_g7":  "Minimizing / Objectives",
    "d2_g8":  "Services / Transactions",
    "d3_g0":  "Misc",
    "d3_g1":  "Death / Sport / Direction",
    "d3_g2":  "School / Production / Cycle",
    "d3_g3":  "Clothing / Container",
    "d4_g0":  "Clothing (derived)",
    "d4_g1":  "Pressure / Container",
    "d5_g0":  "Mix / Blend",
    "d5_g1":  "Answer / Response",
    "d5_g2":  "Sound / Voice",
}

DEFAULT_TIER = 3  # fallback for any cluster not in CLUSTER_TIERS


# ── helpers ───────────────────────────────────────────────────────────────────

def base_name(concept: str) -> str:
    """Strip trailing _N duplicate suffix: 'person_2' → 'person'."""
    return re.sub(r"_\d+$", "", concept).strip()


def deduplicate_concepts(concepts: list[str]) -> list[tuple[str, list[str]]]:
    """
    Group concepts by base name within the list.
    Returns list of (canonical, [all_variants_including_canonical]) sorted by
    allowlist_rank (i.e. preserving the incoming order, which is already
    rank-sorted by the graph builder).

    canonical = the variant that appears first in the incoming list
    (which is the highest-frequency one after allowlist-rank sorting).
    """
    seen_bases: dict[str, str] = {}       # base → canonical
    groups: dict[str, list[str]] = defaultdict(list)

    for c in concepts:
        b = base_name(c)
        if b not in seen_bases:
            seen_bases[b] = c             # first seen = canonical
        groups[seen_bases[b]].append(c)

    # Preserve original order of canonicals
    order = list(dict.fromkeys(seen_bases[base_name(c)] for c in concepts))
    return [(canon, groups[canon]) for canon in order]


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print summary only; don't write files")
    args = parser.parse_args()

    print("=== Curriculum Order Builder ===\n")

    graph_path = ROOT / "inventory" / "curriculum_graph.json"
    print(f"Loading {graph_path}...")
    with open(graph_path) as f:
        graph = json.load(f)

    nodes: dict[str, dict] = graph["nodes"]
    curriculum: list[dict] = graph["curriculum"]

    # ── Assign tiers and sort groups ─────────────────────────────────────────
    ordered_groups: list[dict] = []
    untiered: list[str] = []

    for grp in curriculum:
        cid = grp["cluster"]
        tier = CLUSTER_TIERS.get(cid, DEFAULT_TIER)
        if cid not in CLUSTER_TIERS:
            untiered.append(cid)
        ordered_groups.append({
            "cluster": cid,
            "label": CLUSTER_LABELS.get(cid, cid),
            "tier": tier,
            "depth": grp["depth"],
            "concepts_raw": grp["concepts"],   # full list including _N variants
        })

    if untiered:
        print(f"  ⚠ {len(untiered)} clusters without explicit tier (using default {DEFAULT_TIER}):")
        for cid in untiered:
            print(f"    {cid}")

    # Sort: primary = tier, secondary = depth (hard constraint), tertiary = cluster id
    ordered_groups.sort(key=lambda g: (g["tier"], g["depth"], g["cluster"]))

    # ── Deduplicate within each group ────────────────────────────────────────
    total_raw = sum(len(g["concepts_raw"]) for g in ordered_groups)
    total_canonical = 0
    total_variants = 0

    for grp in ordered_groups:
        deduped = deduplicate_concepts(grp["concepts_raw"])
        grp["concepts_deduped"] = deduped  # [(canonical, [variants])]
        n_canon = len(deduped)
        n_var = sum(len(vs) - 1 for _, vs in deduped)
        total_canonical += n_canon
        total_variants += n_var

    print(f"  {total_raw} raw concepts → {total_canonical} canonical"
          f" + {total_variants} variants collapsed")
    print(f"  {len(ordered_groups)} groups across 5 tiers\n")

    # ── Summary table ─────────────────────────────────────────────────────────
    from collections import Counter
    tier_summary: dict[int, list] = defaultdict(list)
    for grp in ordered_groups:
        tier_summary[grp["tier"]].append(grp)

    TIER_NAMES = {
        1: "Phase A — Concrete anchors",
        2: "Phase B — Concrete relations",
        3: "Phase C — Agents and social world",
        4: "Phase D — Processes and systems",
        5: "Phase E — Abstraction",
    }

    print("── Tier summary ─────────────────────────────────────────────────")
    for t in sorted(tier_summary):
        groups = tier_summary[t]
        n_concepts = sum(len(g["concepts_raw"]) for g in groups)
        n_canon = sum(len(g["concepts_deduped"]) for g in groups)
        print(f"  Tier {t} — {TIER_NAMES[t]}")
        print(f"    {len(groups)} groups, {n_concepts} raw concepts ({n_canon} canonical)")
        for grp in groups:
            n_c = len(grp["concepts_deduped"])
            top4 = [base_name(c) for c, _ in grp["concepts_deduped"][:4]]
            more = f"+{n_c-4}" if n_c > 4 else ""
            print(f"    [{grp['depth']}] {grp['label']:35s}  {top4} {more}")
        print()

    if args.dry_run:
        print("[dry-run] Not writing files.")
        return

    # ── Write curriculum_order.json ──────────────────────────────────────────
    order_json_path = ROOT / "training" / "corpus_admin" / "curriculum_order.json"
    order_json_path.parent.mkdir(parents=True, exist_ok=True)

    order_records = []
    for seq, grp in enumerate(ordered_groups, 1):
        record = {
            "seq": seq,
            "cluster": grp["cluster"],
            "label": grp["label"],
            "tier": grp["tier"],
            "depth": grp["depth"],
            "concepts": [
                {
                    "canonical": base_name(canon),
                    "variants": [base_name(v) for v in variants],
                    "all_keys": variants,   # original keys including _N (for file lookup)
                }
                for canon, variants in grp["concepts_deduped"]
            ],
        }
        order_records.append(record)

    with open(order_json_path, "w", encoding="utf-8") as f:
        json.dump({"groups": order_records}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {order_json_path}  ({order_json_path.stat().st_size // 1024} KB)")

    # ── Write curriculum_manifest.md ─────────────────────────────────────────
    manifest_path = ROOT / "training" / "corpus_admin" / "curriculum_manifest.md"

    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("# Curriculum Manifest (tiered)\n\n")
        f.write("> Generated by `meta/scripts/build_curriculum_order.py`.\n")
        f.write("> Edit `CLUSTER_TIERS` and `CLUSTER_LABELS` in that script to adjust.\n")
        f.write("> **Review before building training chunks.**\n\n")
        f.write(f"**Concepts:** {total_canonical} canonical"
                f" ({total_variants} variants collapsed) | "
                f"**Groups:** {len(ordered_groups)}\n\n")

        f.write("## Overview\n\n")
        f.write("| Phase | Name | Groups | Concepts |\n")
        f.write("|-------|------|--------|----------|\n")
        phase_letter = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}
        for t in sorted(tier_summary):
            groups = tier_summary[t]
            n_c = sum(len(g["concepts_deduped"]) for g in groups)
            f.write(f"| {phase_letter[t]} | {TIER_NAMES[t]} | {len(groups)} | {n_c} |\n")
        f.write("\n---\n")

        cur_tier = -1
        for seq, grp in enumerate(ordered_groups, 1):
            t = grp["tier"]
            depth = grp["depth"]
            label = grp["label"]
            cid = grp["cluster"]
            deduped = grp["concepts_deduped"]
            n_canon = len(deduped)
            n_var = sum(len(vs) - 1 for _, vs in deduped)

            if t != cur_tier:
                f.write(f"\n## {TIER_NAMES[t]}\n\n")
                cur_tier = t

            var_note = f" ({n_var} variants collapsed)" if n_var else ""
            f.write(f"### #{seq} `{cid}` — {label}  "
                    f"[depth {depth}] [{n_canon} concepts{var_note}]\n\n")

            # Prerequisites (hard) from the graph
            all_prereqs: set[str] = set()
            for canon, variants in deduped:
                for v in variants:
                    nd = nodes.get(v, {})
                    all_prereqs.update(nd.get("prerequisites", []))
            all_prereqs -= set(grp["concepts_raw"])
            if all_prereqs:
                ps = ", ".join(sorted(base_name(p) for p in all_prereqs)[:12])
                if len(all_prereqs) > 12:
                    ps += f" … +{len(all_prereqs)-12} more"
                f.write(f"**Prerequisites:** {ps}\n\n")

            # Soft hints from the graph
            all_soft: set[str] = set()
            for canon, variants in deduped:
                for v in variants:
                    nd = nodes.get(v, {})
                    all_soft.update(nd.get("soft_hints", []))
            all_soft -= set(grp["concepts_raw"])
            all_soft -= all_prereqs
            if all_soft:
                ss = ", ".join(sorted(base_name(s) for s in all_soft)[:8])
                if len(all_soft) > 8:
                    ss += f" … +{len(all_soft)-8} more"
                f.write(f"**Soft hints:** {ss}\n\n")

            # Concept table
            f.write("| Concept | Variants | Phase | Rank |\n")
            f.write("|---------|----------|-------|------|\n")
            for canon, variants in deduped:
                nd = nodes.get(canon, nodes.get(variants[0], {}))
                phase = nd.get("phase", "?")
                rank = nd.get("allowlist_rank", "?")
                var_str = ", ".join(base_name(v) for v in variants[1:]) if len(variants) > 1 else "—"
                f.write(f"| `{base_name(canon)}` | {var_str} | {phase} | {rank} |\n")
            f.write("\n")

    print(f"Wrote {manifest_path}")
    print(f"\n=== Done ===")
    print(f"  Review training/corpus_admin/curriculum_manifest.md")
    print(f"  Edit CLUSTER_TIERS in this script if any tier assignments look wrong")
    print(f"  Then: build per-group training chunks")


if __name__ == "__main__":
    main()
