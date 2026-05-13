#!/usr/bin/env python3
"""
Build inventory/dependency_graph.json from phase file names.

Each file stem in training_data/phases/phase_N/ is a concept node.
The phase number is the curriculum tier (1 = earliest, 6 = latest).
No edges are computed here — that requires reading file content and is a separate pass.

Usage:
  python3 meta/scripts/build_dependency_graph.py [--check]

  --check   Print a summary and exit without writing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT  = Path(__file__).resolve().parent.parent.parent
PHASES_DIR = REPO_ROOT / "training_data" / "phases"
OUTPUT     = REPO_ROOT / "inventory" / "dependency_graph.json"
NUM_PHASES = 6


def collect_nodes() -> dict[str, dict]:
    """Walk phase directories; return {word: {phase, file}} for each .md stem."""
    nodes: dict[str, dict] = {}
    for phase_num in range(1, NUM_PHASES + 1):
        phase_dir = PHASES_DIR / f"phase_{phase_num}"
        if not phase_dir.is_dir():
            print(f"WARNING: {phase_dir} not found — skipping", file=sys.stderr)
            continue
        for f in sorted(phase_dir.glob("*.md")):
            stem = f.stem  # e.g. "sun", "apple_2"
            if stem in nodes:
                # Duplicate across phases — record the earlier phase
                if nodes[stem]["phase"] > phase_num:
                    nodes[stem] = {"phase": phase_num, "file": str(f.relative_to(REPO_ROOT))}
            else:
                nodes[stem] = {"phase": phase_num, "file": str(f.relative_to(REPO_ROOT))}
    return nodes


def main() -> None:
    parser = argparse.ArgumentParser(description="Build dependency_graph.json from phase files")
    parser.add_argument("--check", action="store_true", help="Print summary only, do not write")
    args = parser.parse_args()

    nodes = collect_nodes()

    if not nodes:
        print("ERROR: no phase files found", file=sys.stderr)
        sys.exit(1)

    phase_counts = {}
    for data in nodes.values():
        p = data["phase"]
        phase_counts[p] = phase_counts.get(p, 0) + 1

    print(f"Nodes: {len(nodes)}")
    for p in sorted(phase_counts):
        print(f"  phase_{p}: {phase_counts[p]}")

    if args.check:
        return

    graph = {
        "meta": {
            "description": "Curriculum dependency graph for Ninereeds. Nodes are concept words; phase is the curriculum tier (1=earliest). Edges are not yet computed.",
            "node_count": len(nodes),
            "phase_counts": phase_counts,
        },
        "nodes": nodes,
        "edges": [],
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Written: {OUTPUT}")


if __name__ == "__main__":
    main()
