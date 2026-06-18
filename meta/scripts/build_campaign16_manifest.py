#!/usr/bin/env python3
"""Phase 5: build the Campaign 16 training manifest from Phase 4 dialogue files.

Training order (one block per tier):
  Tier 0  — preschool concrete anchors (no dependencies)
  Tier 1  — preschool tier 1 + kindergarten
  Tier 2  — preschool tier 2 + grade 1
  Tier 3  — preschool tier 3 + grade 2
  Tier 4  — grade 3
  Tier 5  — grade 4
  Tier 6  — grade 5
  Tier 7  — grade 6
  Tier 8  — grade 7
  Tier 9  — grade 8

Within each tier: round-robin across domains (consistent alphabetical order).
Preschool nodes:  4 files per node (en → de → jp → zh consecutively).
K-8 nodes:        1 file per node (language assigned by domain).

Output:
  training/corpus_admin/campaign16_manifest.txt
  training/corpus_admin/campaign16_blocks/tier_N.txt  (one per tier, for verification)

Usage:
  python3 meta/scripts/build_campaign16_manifest.py [--dry-run] [--verify]
"""

import argparse, collections, json, pathlib, re, sys

ROOT      = pathlib.Path(__file__).resolve().parents[2]
DIALOGUES = ROOT / "training_data" / "04_education" / "dialogues"
P1_PRE    = ROOT / "training_data" / "04_education" / "phase1_preschool.jsonl"
P1_K8     = ROOT / "training_data" / "04_education" / "phase1_k8.jsonl"
OUT_DIR   = ROOT / "training" / "corpus_admin"
BLOCKS    = OUT_DIR / "campaign16_blocks"

# ── Language assignment (mirrors phase4_gen.py) ───────────────────────────────

GRADE_BAND = {
    "kindergarten": "band_a",
    "grade1": "band_a", "grade2": "band_a",
    "grade3": "band_b", "grade4": "band_b", "grade5": "band_b",
    "grade6": "band_c", "grade7": "band_c", "grade8": "band_c",
}

DOMAIN_LANG_K8 = {
    "language": "en", "math": "zh", "time": "jp", "science": "de",
    "arts": "en", "civics": "en", "economics": "en",
    "health": "en", "social_emotional": "en",
}

def k8_lang(node: dict) -> str:
    domain = node["domain"]
    if domain == "geography":
        return "jp" if "human" in node.get("sub_domain", "") else "de"
    return DOMAIN_LANG_K8.get(domain, "en")

def node_langs(node: dict) -> list[str]:
    if node["grade_level"] == "preschool":
        return ["en", "de", "jp", "zh"]
    return [k8_lang(node)]

# ── Output path (mirrors phase4_gen.py) ──────────────────────────────────────

def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", s.lower().replace(" ", "_").replace("-", "_"))

def get_relpath(node: dict, lang: str) -> str:
    domain = node["domain"]
    sub    = _slug(node["sub_domain"])
    grade  = node["grade_level"]
    if grade == "preschool":
        dirpath = DIALOGUES / "preschool" / domain
    else:
        dirpath = DIALOGUES / "k8" / GRADE_BAND[grade] / domain
    return str((dirpath / f"{domain}_{sub}_{lang}.md").relative_to(ROOT))

# ── Round-robin interleaver ───────────────────────────────────────────────────

def interleave_by_domain(nodes: list[dict]) -> list[dict]:
    """Round-robin across domains (sorted alphabetically for reproducibility)."""
    by_domain: dict[str, list] = collections.defaultdict(list)
    for n in nodes:
        by_domain[n["domain"]].append(n)
    # Stable sort within each domain by id
    for domain in by_domain:
        by_domain[domain].sort(key=lambda n: n["id"])
    domain_order = sorted(by_domain.keys())
    queues = [collections.deque(by_domain[d]) for d in domain_order]

    result = []
    while any(queues):
        for q in queues:
            if q:
                result.append(q.popleft())
    return result

# ── Load Phase 1 nodes ────────────────────────────────────────────────────────

def load_nodes() -> list[dict]:
    nodes = []
    for f in [P1_PRE, P1_K8]:
        for line in f.read_text().splitlines():
            if line.strip():
                nodes.append(json.loads(line))
    return nodes

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print stats without writing files")
    ap.add_argument("--verify",  action="store_true", help="check all manifest paths exist on disk")
    args = ap.parse_args()

    nodes = load_nodes()
    max_tier = max(n["tier"] for n in nodes)

    all_paths: list[str] = []
    tier_blocks: dict[int, list[str]] = {}
    missing: list[str] = []

    for tier in range(max_tier + 1):
        tier_nodes = [n for n in nodes if n["tier"] == tier]
        ordered    = interleave_by_domain(tier_nodes)

        tier_paths = []
        for node in ordered:
            for lang in node_langs(node):
                rel = get_relpath(node, lang)
                tier_paths.append(rel)
                if args.verify and not (ROOT / rel).exists():
                    missing.append(rel)

        tier_blocks[tier] = tier_paths
        all_paths.extend(tier_paths)

    # ── Report ────────────────────────────────────────────────────────────────
    preschool_count = sum(1 for p in all_paths if "preschool" in p)
    k8_count        = len(all_paths) - preschool_count
    print(f"Campaign 16 manifest: {len(all_paths)} files total")
    print(f"  Preschool : {preschool_count} files (39 nodes × 4 langs)")
    print(f"  K-8       : {k8_count} files (262 nodes × 1 lang)")
    print()
    for tier, paths in tier_blocks.items():
        tier_nodes = [n for n in nodes if n["tier"] == tier]
        grades     = sorted(set(n["grade_level"] for n in tier_nodes))
        domains    = sorted(set(n["domain"] for n in tier_nodes))
        print(f"  Tier {tier}: {len(paths):>3} files | {len(tier_nodes):>2} nodes | "
              f"grades: {', '.join(grades[:3])}{'…' if len(grades)>3 else ''} | "
              f"domains: {len(domains)}")

    if args.verify:
        if missing:
            print(f"\n⚠ {len(missing)} missing files:")
            for p in missing:
                print(f"  {p}")
            sys.exit(1)
        else:
            print(f"\n✓ All {len(all_paths)} files verified on disk.")

    if args.dry_run:
        print("\n[dry-run] Nothing written.")
        return

    # ── Write manifest ────────────────────────────────────────────────────────
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BLOCKS.mkdir(parents=True, exist_ok=True)

    manifest = OUT_DIR / "campaign16_manifest.txt"
    header = (
        "# Campaign 16 — Education corpus training manifest\n"
        "# Order: Tier 0 (preschool anchors) → Tier 9 (grade 8)\n"
        "# Within tier: round-robin by domain; preschool nodes: en/de/jp/zh\n"
        f"# Total files: {len(all_paths)}\n"
        "# Generated by: meta/scripts/build_campaign16_manifest.py\n"
        "#\n"
    )
    lines = [header]
    for tier, paths in tier_blocks.items():
        tier_nodes = [n for n in nodes if n["tier"] == tier]
        grades     = sorted(set(n["grade_level"] for n in tier_nodes))
        lines.append(f"\n# ── Tier {tier} ({', '.join(grades)}) {'─'*40}\n")
        lines.extend(p + "\n" for p in paths)

    manifest.write_text("".join(lines))
    print(f"\nWrote {manifest.relative_to(ROOT)}")

    for tier, paths in tier_blocks.items():
        block_file = BLOCKS / f"tier_{tier}.txt"
        block_file.write_text("\n".join(paths) + "\n")
    print(f"Wrote {len(tier_blocks)} block files to {BLOCKS.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
