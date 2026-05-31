"""
Build training order JSONL(s) for teaching stories.

Curriculum ordering: physical → social/behavioral → emotional → cognitive →
                     communication → temporal → abstract → math

Within each domain cluster, sort by entry_tier (simpler first) then label.

Default: one combined file  teaching_stories_order.jsonl
--split:  four phase files  phase_C_order.jsonl  (tier 1 — physical/observable)
                            phase_D_order.jsonl  (tier 2 — causality/emotion)
                            phase_E_order.jsonl  (tier 3 — cognitive/temporal/abstract)
                            phase_F_order.jsonl  (tier 4 — dialogue/math ceiling)

Usage:
  python3 meta/scripts/build_teaching_stories_order.py [--dry-run] [--split]

Reads:  tmp/phase_vocab.jsonl
        training_data/teaching_stories/*.md
Writes: training/training_order/teaching_stories_order.jsonl  (default)
     or training/training_order/phase_{C,D,E,F}_order.jsonl   (--split)
"""

import argparse
import json
import re
from pathlib import Path

REPO        = Path(__file__).resolve().parents[2]
VOCAB_FILE  = REPO / "tmp/phase_vocab.jsonl"
STORIES_DIR = REPO / "training_data/teaching_stories"
OUT_FILE    = REPO / "training/training_order/teaching_stories_order.jsonl"

# ---------------------------------------------------------------------------
# Curriculum domain ordering
# Physical → Social → Emotional → Cognitive → Communication
# → Temporal → Abstract → Math
# ---------------------------------------------------------------------------

# (domain_tag, group_name, probe_after_group)
DOMAIN_ORDER = [
    # --- Physical (directly observable, entry_tier 1) ---
    ("movement_physical_actions",   "physical",     False),
    ("body_parts_actions",          "physical",     False),
    ("outdoor_terrain",             "physical",     False),
    ("construction_structural",     "physical",     False),
    ("pressure_container",          "physical",     False),
    ("clothing_container",          "physical",     False),
    ("clothing_derived",            "physical",     False),
    ("sound_voice",                 "physical",     True),   # probe: end of physical

    # --- Social / behavioral (entry_tier 1–2) ---
    ("domestic_places_services",    "social",       False),
    ("travel_movement",             "social",       False),
    ("separation_departure",        "social",       False),
    ("body_measure_style",          "social",       False),
    ("basic_verbs_desire",          "social",       False),
    ("actions_care_life",           "social",       False),
    ("people_persons",              "social",       False),
    ("life_social_abstract",        "social",       False),
    ("social_people_places",        "social",       False),
    ("common_verbs",                "social",       False),
    ("processes_operations",        "social",       False),
    ("society_institutions",        "social",       False),
    ("progression_change",          "social",       False),
    ("medical_health",              "social",       False),
    ("death_sport_direction",       "social",       False),
    ("mix_blend",                   "social",       False),
    ("misc",                        "social",       False),
    ("services_transactions",       "social",       True),   # probe: end of social

    # --- Emotional (entry_tier 2) ---
    ("emotions_feelings",           "emotional",    True),   # probe: end of emotional

    # --- Cognitive (entry_tier 2–3) ---
    ("basic_cognitive_verbs",       "cognitive",    False),
    ("knowledge_truth",             "cognitive",    False),
    ("knowledge_abstract",          "cognitive",    False),
    ("answer_response",             "cognitive",    True),   # probe: end of cognitive

    # --- Communication / reasoning (entry_tier 2–3) ---
    ("communication_reasoning",     "communication", True),  # probe: end of communication

    # --- School / production ---
    ("school_production_cycle",     "school",       False),
    ("initiation_setup",            "school",       True),   # probe: end of school

    # --- Temporal (entry_tier 3) ---
    ("time_sequence",               "temporal",     False),
    ("time_quantity",               "temporal",     True),   # probe: end of temporal

    # --- Abstract (entry_tier 3) ---
    ("abstract_concepts_info",      "abstract",     False),
    ("abstract_properties",         "abstract",     False),
    ("abstract_states",             "abstract",     False),
    ("visual_abstract_forms",       "abstract",     False),
    ("progressive_actions",         "abstract",     False),
    ("culture_study_media",         "abstract",     True),   # probe: end of abstract

    # --- Math (entry_tier 3–4) ---
    ("math_numbers",                "math",         True),   # probe: end of math
]

DOMAIN_POSITION = {d: i for i, (d, _, _) in enumerate(DOMAIN_ORDER)}
DOMAIN_TO_GROUP = {d: g for d, g, _ in DOMAIN_ORDER}
PROBE_DOMAINS   = {d for d, _, p in DOMAIN_ORDER if p}


def safe_stem(label: str) -> str:
    return re.sub(r"[^\w\-]", "_", label).strip("_")


def sort_key(r: dict) -> tuple:
    domain    = r["domains"][0] if r["domains"] else "unknown"
    pos       = DOMAIN_POSITION.get(domain, 999)
    tier      = r.get("entry_tier", 2)
    return (pos, tier, r["label"])


TIER_TO_PHASE = {1: "C", 2: "D", 3: "E", 4: "F"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--split",   action="store_true",
                    help="Write separate phase_C/D/E/F_order.jsonl files by entry_tier")
    args = ap.parse_args()

    # Load vocab
    vocab = {
        r["label"]: r
        for r in (json.loads(l) for l in VOCAB_FILE.read_text().splitlines() if l.strip())
        if r.get("tier") == 1 and "manifestations" in r
    }

    # Find generated story files
    if not STORIES_DIR.exists():
        print(f"Stories dir not found: {STORIES_DIR}")
        print("Run story_gen_batch.py first.")
        return

    story_files = {p.stem: p for p in STORIES_DIR.glob("*.md")}

    # Match vocab entries to story files
    matched   = []
    no_file   = []
    no_schema = []

    for label, record in vocab.items():
        stem = safe_stem(label)
        if stem in story_files:
            matched.append(record)
        else:
            no_file.append(label)

    # Sort by curriculum order
    matched.sort(key=sort_key)

    # Build JSONL records
    records  = []
    last_domain_in_group: dict[str, int] = {}

    for i, r in enumerate(matched):
        domain = r["domains"][0] if r["domains"] else "unknown"
        group  = DOMAIN_TO_GROUP.get(domain, "unknown")
        last_domain_in_group[domain] = i

    # Determine probe positions: last entry of each probe-domain
    probe_positions: set[int] = set()
    for domain in PROBE_DOMAINS:
        if domain in last_domain_in_group:
            probe_positions.add(last_domain_in_group[domain])

    for seq, r in enumerate(matched, start=1):
        label  = r["label"]
        stem   = safe_stem(label)
        domain = r["domains"][0] if r["domains"] else "unknown"
        group  = DOMAIN_TO_GROUP.get(domain, "unknown")
        tier   = r.get("entry_tier", 2)

        record = {
            "unit_id":       f"TS_{seq:04d}",
            "label":         label,
            "depth":         tier,
            "cluster":       f"ts_{group}",
            "allowlist_rank": 9999,
            "source_keys":   [stem],
            "files":         [f"training_data/teaching_stories/{stem}.md"],
            "tags":          [
                "teaching_stories",
                domain,
                f"cluster:ts_{group}",
                f"depth:{tier}",
            ],
            "probe_after":   (seq - 1) in probe_positions,
        }
        records.append(record)

    # Summary
    from collections import Counter
    group_counts  = Counter(DOMAIN_TO_GROUP.get(r["domains"][0] if r["domains"] else "?", "unknown")
                            for r in matched)
    probe_count   = sum(1 for r in records if r["probe_after"])
    domain_counts = Counter(r["domains"][0] if r["domains"] else "unknown"
                            for r in matched)

    print(f"Story files found:   {len(story_files)}")
    print(f"Matched to vocab:    {len(matched)}")
    print(f"Missing story files: {len(no_file)}")
    print(f"Probe points:        {probe_count}")
    print()
    print("Curriculum groups:")
    for group, count in group_counts.most_common():
        print(f"  {group:<20} {count}")
    print()

    if no_file[:10]:
        print(f"First 10 without story file:")
        for l in no_file[:10]:
            print(f"  {l}")
        if len(no_file) > 10:
            print(f"  ... and {len(no_file) - 10} more")
        print()

    if args.dry_run:
        if args.split:
            from collections import Counter
            tier_counts = Counter(r["depth"] for r in records)
            print("Split output (--split):")
            for tier in sorted(tier_counts):
                phase = TIER_TO_PHASE.get(tier, f"tier{tier}")
                print(f"  phase_{phase}_order.jsonl  — tier {tier}: {tier_counts[tier]} units")
        print("Dry run — not writing.")
        return

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    if args.split:
        from collections import defaultdict
        by_tier: dict[int, list] = defaultdict(list)
        # Re-sequence within each tier
        for r in records:
            by_tier[r["depth"]].append(r)

        written = []
        for tier in sorted(by_tier):
            phase    = TIER_TO_PHASE.get(tier, f"tier{tier}")
            out_path = OUT_FILE.parent / f"phase_{phase}_order.jsonl"
            tier_records = by_tier[tier]
            # Renumber unit_ids within each phase
            for i, r in enumerate(tier_records, start=1):
                r["unit_id"] = f"{phase}_{i:04d}"
                r["tags"]    = [t if not t.startswith("teaching_stories")
                                else f"phase_{phase}" for t in r["tags"]]
                r["tags"].insert(0, f"phase_{phase}")
            with open(out_path, "w") as f:
                for r in tier_records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            written.append((out_path, len(tier_records)))
            print(f"Written: {out_path}  ({len(tier_records)} units)")

        total = sum(c for _, c in written)
        print(f"\nTotal: {total} units across {len(written)} phase files")
    else:
        with open(OUT_FILE, "w") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"Written: {OUT_FILE}  ({len(records)} units)")


if __name__ == "__main__":
    main()
