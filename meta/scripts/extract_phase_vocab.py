"""
Extract concept labels from phase A-E JSONL order files and assign initial
living-list tier state.

Tier definitions:
  1 — needs anchor story (new to Ninereeds: phases B, D, E)
  2 — has been anchor, needs supporting exposure (phases A, C)
  3 — covered (not assigned here; reserved for post-generation promotion)

If a label appears in both a Tier-2 phase and a Tier-1 phase, it takes Tier 2
(already taught as anchor — the B/D/E file was a duplicate entry).

Output: tmp/phase_vocab.jsonl
  {"label": "worry", "tier": 1, "phases": ["B"], "domains": ["emotions_feelings"]}
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parents[2]

PHASE_FILES = {
    "A": REPO / "training/training_order/phase_A_order.jsonl",
    "B": REPO / "training/training_order/phase_B_order.jsonl",
    "C": REPO / "training/training_order/phase_C_order.jsonl",
    "D": REPO / "training/training_order/phase_D_order.jsonl",
    "E": REPO / "training/training_order/phase_E_order.jsonl",
}

# Phases already taught as anchors → supporting exposure only
TIER_2_PHASES = {"A", "C"}
# Phases new to Ninereeds → need anchor stories
TIER_1_PHASES = {"B", "D", "E"}

# Function/grammar words to exclude
GRAMMAR = {
    "a", "an", "the", "this", "that", "these", "those",
    "i", "you", "he", "she", "it", "we", "they",
    "me", "him", "her", "us", "them",
    "my", "your", "his", "its", "our", "their",
    "who", "which", "what", "where", "when", "why", "how",
    "and", "but", "or", "nor", "so", "yet", "for",
    "in", "on", "at", "by", "of", "to", "up", "as",
    "with", "from", "into", "onto", "upon", "about",
    "over", "under", "after", "before", "since", "until",
    "through", "between", "among", "against", "along",
    "be", "is", "are", "was", "were", "been", "being",
    "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might",
    "must", "shall", "can", "need", "dare",
    "not", "no", "nor",
    "all", "both", "each", "every", "any", "some",
    "other", "another", "such", "same",
    "also", "just", "only", "very", "too", "quite",
    "then", "now", "here", "there", "still", "already",
    "again", "never", "always", "often",
    "if", "unless", "until", "while", "although", "because",
    "therefore", "thus", "however",
}


def domain_tags(tags):
    return [
        t for t in tags
        if not t.startswith("phase_")
        and not t.startswith("cluster:")
        and not t.startswith("depth:")
    ]


def main():
    # label → {phases: set, domains: set}
    entries = defaultdict(lambda: {"phases": set(), "domains": set()})

    for phase, path in PHASE_FILES.items():
        with open(path) as f:
            for line in f:
                u = json.loads(line)
                label = u["label"].strip().lower()
                if label in GRAMMAR:
                    continue
                entries[label]["phases"].add(phase)
                entries[label]["domains"].update(domain_tags(u.get("tags", [])))

    # Assign tier: any appearance in A or C → Tier 2; B/D/E only → Tier 1
    records = []
    for label, data in sorted(entries.items()):
        phases = data["phases"]
        tier = 2 if phases & TIER_2_PHASES else 1
        records.append({
            "label": label,
            "tier": tier,
            "phases": sorted(phases),
            "domains": sorted(data["domains"]),
        })

    # Sort: Tier 1 first (needs work), then Tier 2, alpha within tier
    records.sort(key=lambda r: (r["tier"], r["label"]))

    out = REPO / "tmp/phase_vocab.jsonl"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Summary
    t1 = [r for r in records if r["tier"] == 1]
    t2 = [r for r in records if r["tier"] == 2]
    overlap = [r for r in records if len(r["phases"]) > 1]

    print(f"Total unique labels: {len(records)}")
    print(f"  Tier 1 (need anchor story — B/D/E only): {len(t1)}")
    print(f"  Tier 2 (need supporting exposure — A/C):  {len(t2)}")
    print(f"  Labels appearing in multiple phases:       {len(overlap)}")
    print()
    print(f"Output: {out}")

    # Domain breakdown for Tier 1
    from collections import Counter
    t1_domains = Counter(d for r in t1 for d in r["domains"])
    print("\nTier 1 domain breakdown:")
    for domain, count in t1_domains.most_common():
        print(f"  {domain}: {count}")


if __name__ == "__main__":
    main()
