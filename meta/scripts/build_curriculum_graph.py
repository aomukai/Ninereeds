#!/usr/bin/env python3
"""
Build inventory/curriculum_graph.json with dependency edges, topological depths,
and semantic clusters for training order planning.

Run with the project Python:
  /home/aomukai/.unsloth/studio/unsloth_studio/bin/python meta/scripts/build_curriculum_graph.py

Method:
  For each EN phase file, scan [Ninereeds] lines for mentions of other known
  concepts. Each mention creates an edge: mentioned_concept → this_concept
  (meaning: train mentioned_concept before this one).

  Topological depth is computed (Kahn BFS). Cycles are grouped at the same
  depth. Within each depth, concepts are clustered by semantic domain using
  sentence-transformers, then sorted by allowlist frequency.

Outputs:
  inventory/curriculum_graph.json          enriched graph (edges, depths, clusters)
  training/corpus_admin/curriculum_manifest.md  human-readable manifest for review

Usage:
  python meta/scripts/build_curriculum_graph.py [--dry-run] [--no-embed] [--clusters N]

  --dry-run     Build graph, print summary, but don't write output files
  --no-embed    Skip sentence-transformer clustering (depth + frequency only)
  --clusters N  Clusters per depth level; 0 = auto (default: 0)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # Ninereeds/

# ── adjective / modifier stoplist ────────────────────────────────────────────
# Words in this set, when appearing WITHOUT an article after "is/are/was",
# are treated as predicate adjectives and do NOT create prerequisite edges.
# They still create edges if they appear after "is a/an" (i.e. used as nouns).
ADJECTIVE_STOPLIST: frozenset[str] = frozenset({
    # size / extent
    "small", "large", "big", "tiny", "huge", "little", "great", "tall", "short",
    "long", "wide", "narrow", "thick", "thin", "deep", "shallow", "high", "low",
    "heavy", "light", "dense",
    # colour
    "red", "blue", "green", "yellow", "orange", "purple", "pink",
    "black", "white", "brown", "grey", "gray", "pale", "dark", "bright", "clear",
    # texture / surface
    "rough", "smooth", "soft", "hard", "sharp", "blunt", "slippery",
    "flat", "round", "curved", "straight", "bumpy",
    # temperature / state
    "hot", "cold", "warm", "cool", "wet", "dry", "solid", "liquid", "frozen",
    # speed / intensity
    "fast", "slow", "loud", "quiet", "silent", "strong", "weak", "gentle",
    # age / condition
    "old", "new", "young", "fresh", "ancient", "modern", "clean", "dirty",
    # misc property words that commonly appear as predicate adjectives
    "open", "closed", "full", "empty", "alive", "dead", "real", "safe", "wild",
    "common", "rare", "plain", "simple", "natural", "raw", "cooked",
    "sticky", "sweet", "sour", "bitter", "salty",
})


# ── I/O helpers ───────────────────────────────────────────────────────────────

def load_base_graph() -> dict:
    path = ROOT / "inventory" / "dependency_graph.json"
    with open(path) as f:
        return json.load(f)


def load_allowlist() -> dict[str, int]:
    """Return word → rank (0 = most frequent)."""
    path = ROOT / "inventory" / "allowlist.txt"
    rank: dict[str, int] = {}
    with open(path) as f:
        for i, line in enumerate(f):
            w = line.strip().lower()
            if w:
                rank[w] = i
    return rank


def find_en_files(phase_dirs: list[Path]) -> dict[str, Path]:
    """
    Scan phase directories; return lowercase_stem → path for EN files only.
    EN files have no _DE / _JP / _ZH suffix.  Multi-word stems keep spaces.
    """
    result: dict[str, Path] = {}
    lang_suffixes = ("_DE", "_JP", "_ZH", "_de", "_jp", "_zh")
    for d in phase_dirs:
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md")):
            if any(p.stem.endswith(s) for s in lang_suffixes):
                continue
            result[p.stem.lower()] = p
    return result


def read_first_definition_line(path: Path) -> str:
    """
    Return only the first [Ninereeds] line from the first block.
    This is the primary definition ("An acorn is a nut.") — the IS-A
    relationship that encodes true prerequisites.  Scanning all body text
    produces too many contextual mentions that aren't real prerequisites.
    """
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.startswith("[Ninereeds]"):
                return raw[len("[Ninereeds]"):].strip().lower()
    except Exception:
        pass
    return ""


# ── concept mention detection ─────────────────────────────────────────────────

# Suffix stripping rules: (suffix_to_remove, optional_replacement)
_SUFFIX_RULES = [
    ("'s", ""), ("s", ""), ("es", ""), ("ies", "y"),
    ("ing", ""), ("ing", "e"),   # running→run, hoping→hope
    ("ed", ""), ("ed", "e"),
    ("er", ""), ("er", "e"),
    ("est", ""), ("ly", ""), ("ness", ""), ("ful", ""),
]


def lemmatize(word: str, concepts: set[str]) -> str | None:
    """Match an inflected word to a known concept, or return None."""
    w = word.lower()
    if w in concepts:
        return w
    for suffix, repl in _SUFFIX_RULES:
        if w.endswith(suffix) and len(w) > len(suffix) + 2:
            base = w[: -len(suffix)] + repl
            if base in concepts:
                return base
    return None


def find_mentions(text: str, single_concepts: set[str],
                  multi_concepts: list[str]) -> list[tuple[str, str]]:
    """
    Find all concept mentions in text.  Returns list of (canonical_concept, token_in_text).
    Multi-word phrases matched first (longest → shortest) to prevent partial re-matching.
    """
    results: list[tuple[str, str]] = []
    seen: set[str] = set()
    # Multi-word: substring match; blank out matched span
    for mc in multi_concepts:
        if mc in text and mc not in seen:
            results.append((mc, mc))
            seen.add(mc)
            text = text.replace(mc, " " * len(mc))
    # Single-word: tokenise + lemmatize
    for tok in re.findall(r"[a-z']+", text):
        canon = lemmatize(tok, single_concepts)
        if canon and canon not in seen:
            results.append((canon, tok))
            seen.add(canon)
    return results


def get_edge_type(definition: str, token: str, canonical: str) -> tuple[str, str]:
    """
    Classify the relationship between a definition sentence and a matched concept.
    Returns (edge_type, confidence).

    edge_type | confidence | meaning
    ----------|------------|--------
    IS-A      | HIGH       | "X is a/an TOKEN" — hypernym
    HAS       | MEDIUM     | "X has TOKEN" / "X has a/an TOKEN" — part or attribute
    MADE-OF   | MEDIUM     | "X is made of TOKEN"
    PROPERTY  | SKIP       | TOKEN is a modifier/adjective, not a noun head
    GENERAL   | LOW        | TOKEN mentioned but pattern unclear
    """
    m = re.search(r"\b" + re.escape(token) + r"\b", definition)
    if not m:
        m = re.search(r"\b" + re.escape(canonical) + r"\b", definition)
    if not m:
        return ("GENERAL", "LOW")

    before = definition[: m.start()].rstrip()
    before_words = before.split()

    # IS-A: "is/are/was a/an/the TOKEN"
    # Guard: if canonical is in the adj stoplist it's a modifier ("is a tall tree"),
    # not the noun head → skip.
    if re.search(r"\b(is|are|was)\s+(a|an|the)\s*$", before):
        if canonical in ADJECTIVE_STOPLIST:
            return ("PROPERTY", "SKIP")
        return ("IS-A", "HIGH")

    # HAS: "has/have/had [optional words] TOKEN"
    # Check word-by-word because rstrip() removes trailing spaces that the
    # regex `(\w+\s+)?` relies on.
    _HAS_VERBS = {"has", "have", "had"}
    if before_words:
        last = before_words[-1]
        second_last = before_words[-2] if len(before_words) >= 2 else ""
        if last in _HAS_VERBS or second_last in _HAS_VERBS:
            return ("HAS", "MEDIUM")

    # MADE-OF: "made of/from TOKEN"
    if re.search(r"\bmade\s+(of|from)\s*$", before):
        return ("MADE-OF", "MEDIUM")

    # PROPERTY: "is/are/was TOKEN" (bare predicate) + TOKEN is an adjective modifier
    if re.search(r"\b(is|are|was)\s*$", before) and canonical in ADJECTIVE_STOPLIST:
        return ("PROPERTY", "SKIP")

    return ("GENERAL", "LOW")


# ── topological depth (Kahn BFS) ──────────────────────────────────────────────

def compute_depths(
    forward_edges: dict[str, set[str]],  # prereq → {dependents}
    all_nodes: set[str],
) -> dict[str, int]:
    """
    Assign a depth to every node.  Nodes with no prerequisites get depth 0.
    Nodes in cycles (unresolvable) get max_depth + 1.
    """
    # Build in-degree and predecessor maps
    in_degree: dict[str, int] = {n: 0 for n in all_nodes}
    for src, dsts in forward_edges.items():
        for dst in dsts:
            if dst in in_degree:
                in_degree[dst] += 1

    depth: dict[str, int] = {}
    queue: deque[str] = deque()

    for n in all_nodes:
        if in_degree[n] == 0:
            depth[n] = 0
            queue.append(n)

    while queue:
        node = queue.popleft()
        for dep in forward_edges.get(node, set()):
            if dep not in all_nodes:
                continue
            in_degree[dep] -= 1
            depth[dep] = max(depth.get(dep, 0), depth[node] + 1)
            if in_degree[dep] == 0:
                queue.append(dep)

    # Cycle survivors: assign max_depth + 1
    max_d = max(depth.values()) if depth else 0
    for n in all_nodes:
        if n not in depth:
            depth[n] = max_d + 1

    return depth


# ── semantic clustering ───────────────────────────────────────────────────────

def cluster_at_depth(
    concepts: list[str],
    n_clusters: int,
) -> list[int]:
    """Return KMeans cluster label for each concept in the list."""
    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import KMeans

    model = SentenceTransformer("all-MiniLM-L6-v2")
    # Use cleaned names (strip _2 suffixes) for embedding
    names = [re.sub(r"_\d+$", "", c).strip() for c in concepts]
    embeddings = model.encode(names, show_progress_bar=False)
    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    return km.fit_predict(embeddings).tolist()


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build curriculum dependency graph with edges, depths, clusters."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print summary only; don't write files")
    parser.add_argument("--no-embed", action="store_true",
                        help="Skip sentence-transformer clustering")
    parser.add_argument("--clusters", type=int, default=0,
                        help="Clusters per depth level (0 = auto, default: 0)")
    args = parser.parse_args()

    print("=== Curriculum Graph Builder ===\n")

    # ── 1. Load inputs ────────────────────────────────────────────────────────
    print("Loading base graph...")
    base = load_base_graph()
    nodes: dict[str, dict] = base["nodes"]
    all_concepts: set[str] = set(nodes.keys())
    print(f"  {len(all_concepts)} concepts")

    print("Loading allowlist...")
    allowlist_rank = load_allowlist()
    print(f"  {len(allowlist_rank)} entries")

    print("Scanning EN phase files...")
    phase_dirs = [ROOT / f"training_data/phases/phase_{i}" for i in range(1, 7)]
    stem_to_file = find_en_files(phase_dirs)
    print(f"  {len(stem_to_file)} EN files found")

    # ── 2. Map concepts → EN file paths ──────────────────────────────────────
    concept_to_file: dict[str, Path] = {}
    for concept in all_concepts:
        key = concept.lower()
        if key in stem_to_file:
            concept_to_file[concept] = stem_to_file[key]
            continue
        # Strip _N duplicate suffix and retry
        clean = re.sub(r"_\d+$", "", concept).strip().lower()
        if clean in stem_to_file:
            concept_to_file[concept] = stem_to_file[clean]

    print(f"  {len(concept_to_file)}/{len(all_concepts)} concepts mapped to files")

    # ── 3. Mine dependency edges ──────────────────────────────────────────────
    print("\nMining corpus for dependency edges...")

    single_concepts: set[str] = {c.lower() for c in all_concepts if " " not in c}
    # Remove _N suffixes from multi-word concepts for phrase matching
    multi_concepts: list[str] = sorted(
        {re.sub(r"_\d+$", "", c).strip().lower()
         for c in all_concepts if " " in c},
        key=len, reverse=True,  # longest first → greedy match
    )

    # Build a normalised concept lookup (handles _N variants)
    norm_to_concept: dict[str, str] = {}
    for c in all_concepts:
        norm = re.sub(r"_\d+$", "", c).strip().lower()
        if norm not in norm_to_concept:
            norm_to_concept[norm] = c  # first seen wins

    # Function words that may be in the concept set but must not create edges.
    # Articles and pronouns in definitions are grammatical noise, not prerequisites.
    FUNCTION_WORD_SKIP: frozenset[str] = frozenset({
        "a", "an", "the", "this", "that", "these", "those",
        "is", "are", "was", "were", "be", "been", "being",
        "it", "its", "he", "she", "they", "we", "you", "i",
        "of", "in", "on", "at", "to", "by", "for", "with",
        "and", "or", "but", "not", "no", "so", "as",
    })

    # hard_edges[prereq] = {dependents} — IS-A, HAS, MADE-OF only; used for depth computation
    # soft_edges[prereq] = {dependents} — GENERAL/LOW; informational only, not used for depth
    hard_edges: dict[str, set[str]] = defaultdict(set)
    soft_edges: dict[str, set[str]] = defaultdict(set)
    # edge_records: full record for every candidate edge (including skipped PROPERTY)
    edge_records: list[dict] = []
    edge_count = 0

    total = len(concept_to_file)
    concept_phase = {c: nodes[c]["phase"] for c in all_concepts}

    for i, (concept, fpath) in enumerate(concept_to_file.items(), 1):
        if i % 500 == 0 or i == total:
            print(f"  {i}/{total} files processed...", end="\r", flush=True)

        # Only scan the primary definition line — "An acorn is a nut."
        # Full-text mining produces O(100K) noisy edges; every concept
        # mentions every other in passing, collapsing all depths to 1.
        text = read_first_definition_line(fpath)
        if not text:
            continue

        self_clean = re.sub(r"_\d+$", "", concept).strip().lower()
        self_tokens = set(self_clean.split())

        for raw_mention, token in find_mentions(text, single_concepts, multi_concepts):
            # Skip function words regardless of whether they're in the concept set
            if raw_mention in FUNCTION_WORD_SKIP:
                continue
            # Skip single-character concepts (noise)
            if len(raw_mention) <= 1:
                continue
            canon = norm_to_concept.get(raw_mention, raw_mention)
            if canon not in all_concepts:
                continue
            if canon == concept:
                continue
            if raw_mention in self_tokens:
                continue
            # Phase guard: only create edge A→B if phase(A) ≤ phase(B).
            if concept_phase.get(canon, 99) > concept_phase.get(concept, 99):
                continue

            edge_type, confidence = get_edge_type(text, token, raw_mention)

            record = {
                "prereq": canon,
                "dependent": concept,
                "type": edge_type,
                "confidence": confidence,
                "source": text,
            }
            edge_records.append(record)

            if confidence != "SKIP":
                if edge_type in ("IS-A", "HAS", "MADE-OF"):
                    hard_edges[canon].add(concept)
                else:
                    soft_edges[canon].add(concept)
                edge_count += 1

    skipped = sum(1 for r in edge_records if r["confidence"] == "SKIP")
    print(f"\n  {edge_count} dependency edges kept  ({skipped} PROPERTY edges skipped)")

    hard_count = sum(len(v) for v in hard_edges.values())
    soft_count = sum(len(v) for v in soft_edges.values())
    print(f"  {hard_count} hard edges (IS-A/HAS/MADE-OF) — used for depth ordering")
    print(f"  {soft_count} soft edges (GENERAL) — informational only")

    # ── 4. Compute topological depths (hard edges only) ───────────────────────
    print("Computing topological depths...")
    depth_map = compute_depths(dict(hard_edges), all_concepts)

    from collections import Counter
    depth_counts = Counter(depth_map.values())
    max_depth = max(depth_map.values())
    print(f"  Max depth: {max_depth}")
    for d in sorted(depth_counts):
        print(f"  Depth {d:2d}: {depth_counts[d]:5d} concepts")

    cycle_nodes = sum(1 for n in all_concepts if n not in depth_map
                      or depth_map[n] == max_depth + 1)
    if cycle_nodes:
        print(f"  ({cycle_nodes} cycle nodes placed at depth {max_depth + 1})")

    # ── 5. Semantic clustering within each depth level ────────────────────────
    print("\nClustering within depth levels...")

    cluster_label: dict[str, str] = {}

    if args.no_embed:
        print("  --no-embed: skipping; using single cluster per depth")
        for concept in all_concepts:
            cluster_label[concept] = f"d{depth_map[concept]}"
    else:
        by_depth: dict[int, list[str]] = defaultdict(list)
        for c in all_concepts:
            by_depth[depth_map[c]].append(c)

        print("  Loading sentence-transformers model (all-MiniLM-L6-v2)...")
        from sentence_transformers import SentenceTransformer
        from sklearn.cluster import KMeans

        st_model = SentenceTransformer("all-MiniLM-L6-v2")

        for d in sorted(by_depth.keys()):
            group = by_depth[d]
            n = len(group)

            if n <= 3:
                for c in group:
                    cluster_label[c] = f"d{d}_g0"
                continue

            k = args.clusters if args.clusters > 0 else max(2, min(20, max(2, int(n**0.5) // 2 + 1)))
            k = min(k, n)

            print(f"  Depth {d}: {n} concepts → {k} clusters       ", end="\r", flush=True)

            names = [re.sub(r"_\d+$", "", c).strip() for c in group]
            embeddings = st_model.encode(names, show_progress_bar=False)
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = km.fit_predict(embeddings).tolist()

            for c, lbl in zip(group, labels):
                cluster_label[c] = f"d{d}_g{lbl}"

        print("  Clustering complete.                              ")

    # ── 6. Sort: depth → cluster → allowlist frequency ───────────────────────
    def sort_key(c: str) -> tuple:
        clean = re.sub(r"_\d+$", "", c).strip().lower()
        rank = allowlist_rank.get(clean, len(allowlist_rank) + 1)
        return (depth_map[c], cluster_label.get(c, ""), rank, c)

    ordered = sorted(all_concepts, key=sort_key)

    # ── 7. Build curriculum groups ────────────────────────────────────────────
    curriculum: list[dict] = []
    cur_depth = -1
    cur_cluster = None
    cur_group: list[str] = []

    for c in ordered:
        d = depth_map[c]
        cl = cluster_label.get(c, "")
        if d != cur_depth or cl != cur_cluster:
            if cur_group:
                curriculum.append({"depth": cur_depth, "cluster": cur_cluster, "concepts": cur_group})
            cur_depth, cur_cluster, cur_group = d, cl, [c]
        else:
            cur_group.append(c)
    if cur_group:
        curriculum.append({"depth": cur_depth, "cluster": cur_cluster, "concepts": cur_group})

    print(f"\n{len(curriculum)} training groups across {max_depth + 1} depth levels")

    # ── 8. Build enriched node records ───────────────────────────────────────
    prereq_of: dict[str, list[str]] = defaultdict(list)
    dependent_of: dict[str, list[str]] = defaultdict(list)
    soft_hints_of: dict[str, list[str]] = defaultdict(list)
    for src, dsts in hard_edges.items():
        for dst in dsts:
            prereq_of[dst].append(src)
            dependent_of[src].append(dst)
    for src, dsts in soft_edges.items():
        for dst in dsts:
            soft_hints_of[dst].append(src)

    enriched_nodes: dict[str, dict] = {}
    for concept, meta in nodes.items():
        clean = re.sub(r"_\d+$", "", concept).strip().lower()
        enriched_nodes[concept] = {
            "phase": meta["phase"],
            "file": meta["file"],
            "depth": depth_map.get(concept, 0),
            "cluster": cluster_label.get(concept, ""),
            "allowlist_rank": allowlist_rank.get(clean, len(allowlist_rank) + 1),
            "prerequisites": sorted(prereq_of.get(concept, [])),
            "dependents": sorted(dependent_of.get(concept, [])),
            "soft_hints": sorted(soft_hints_of.get(concept, [])),
        }

    # Build edge_list: hard edges (IS-A/HAS/MADE-OF) + soft hints (GENERAL).
    # PROPERTY/SKIP edges are excluded entirely.
    seen_pairs: set[tuple[str, str]] = set()
    edge_list = []
    for rec in edge_records:
        if rec["confidence"] == "SKIP":
            continue
        pair = (rec["prereq"], rec["dependent"])
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        edge_list.append({
            "from": rec["prereq"],
            "to": rec["dependent"],
            "type": rec["type"],
            "confidence": rec["confidence"],
            "hard": rec["type"] in ("IS-A", "HAS", "MADE-OF"),
        })

    output_graph = {
        "meta": {
            "description": (
                "Curriculum graph with corpus-mined dependency edges, topological depths, "
                "and sentence-transformer semantic clusters."
            ),
            "node_count": len(enriched_nodes),
            "edge_count": len(edge_list),
            "max_depth": max_depth,
            "group_count": len(curriculum),
        },
        "nodes": enriched_nodes,
        "edges": edge_list,
        "curriculum": curriculum,
    }

    # ── 9. Dry-run summary ────────────────────────────────────────────────────
    if args.dry_run:
        print("\n[dry-run] Would write:")
        print(f"  inventory/curriculum_graph.json")
        print(f"    {len(enriched_nodes)} nodes, {len(edge_list)} edges, {len(curriculum)} groups")
        print(f"  training/corpus_admin/curriculum_manifest.md")

        # Show sample edges including skipped PROPERTY ones
        print(f"\n── Sample edges (up to 40, mixed types) ─────────────────")
        type_order = {"IS-A": 0, "HAS": 1, "MADE-OF": 2, "GENERAL": 3, "PROPERTY": 4}
        sample = sorted(edge_records, key=lambda r: type_order.get(r["type"], 9))
        shown_types: dict[str, int] = defaultdict(int)
        shown = 0
        for rec in sample:
            t = rec["type"]
            if shown_types[t] >= 10:
                continue
            skip_marker = "  [SKIP]" if rec["confidence"] == "SKIP" else "        "
            print(
                f"  {rec['prereq']:22s} → {rec['dependent']:22s}"
                f"  {t:8s} {rec['confidence']:4s}"
                f"{skip_marker}  \"{rec['source'][:60]}\""
            )
            shown_types[t] += 1
            shown += 1
            if shown >= 40:
                break

        print(f"\n── Edge type breakdown ───────────────────────────────────")
        from collections import Counter
        type_counts = Counter(r["type"] for r in edge_records)
        for t in ["IS-A", "HAS", "MADE-OF", "GENERAL", "PROPERTY"]:
            n = type_counts.get(t, 0)
            note = " ← hard, used for depth" if t in ("IS-A", "HAS", "MADE-OF") else \
                   " ← soft hint only"       if t == "GENERAL" else \
                   " ← skipped"
            print(f"  {t:10s}: {n:5d}{note}")

        print(f"\n── Curriculum groups ─────────────────────────────────────")
        for grp in curriculum[:15]:
            sample_c = grp["concepts"][:4]
            more = f" +{len(grp['concepts'])-4}" if len(grp["concepts"]) > 4 else ""
            print(f"  depth={grp['depth']:2d} {grp['cluster']:20s}  {sample_c}{more}")
        return

    # ── 10. Write curriculum_graph.json ───────────────────────────────────────
    out_json = ROOT / "inventory" / "curriculum_graph.json"
    print(f"\nWriting {out_json}...")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(output_graph, f, indent=2, ensure_ascii=False)
    print(f"  Done ({out_json.stat().st_size // 1024} KB)")

    # ── 11. Write curriculum_manifest.md ──────────────────────────────────────
    manifest_dir = ROOT / "training" / "corpus_admin"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "curriculum_manifest.md"

    print(f"Writing {manifest_path}...")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("# Curriculum Manifest\n\n")
        f.write("> Generated by `meta/scripts/build_curriculum_graph.py`.  \n")
        f.write("> **Review this before building training chunks or starting run 13.**  \n")
        f.write("> Edit groups or reorder as needed; the training loop reads this file.\n\n")
        f.write(f"**Concepts:** {len(all_concepts)} | "
                f"**Edges:** {len(edge_list)} | "
                f"**Max depth:** {max_depth} | "
                f"**Groups:** {len(curriculum)}\n\n")
        f.write("---\n")

        cur_d = -1
        for i, grp in enumerate(curriculum, 1):
            d = grp["depth"]
            if d != cur_d:
                f.write(f"\n## Depth {d}\n\n")
                cur_d = d

            concepts = grp["concepts"]
            f.write(f"### Group {i} — `{grp['cluster']}` ({len(concepts)} concepts)\n\n")

            # Hard prerequisites (IS-A / HAS / MADE-OF)
            all_prereqs: set[str] = set()
            for c in concepts:
                all_prereqs.update(enriched_nodes[c]["prerequisites"])
            all_prereqs -= set(concepts)
            if all_prereqs:
                prereq_str = ", ".join(sorted(all_prereqs)[:12])
                if len(all_prereqs) > 12:
                    prereq_str += f" … +{len(all_prereqs)-12} more"
                f.write(f"**Prerequisites (hard):** {prereq_str}\n\n")

            # Soft hints (GENERAL)
            all_soft: set[str] = set()
            for c in concepts:
                all_soft.update(enriched_nodes[c].get("soft_hints", []))
            all_soft -= set(concepts)
            all_soft -= all_prereqs
            if all_soft:
                soft_str = ", ".join(sorted(all_soft)[:10])
                if len(all_soft) > 10:
                    soft_str += f" … +{len(all_soft)-10} more"
                f.write(f"**Soft hints (review):** {soft_str}\n\n")

            f.write("| Concept | Phase | Rank | Depth |\n")
            f.write("|---------|-------|------|-------|\n")
            for c in concepts:
                nd = enriched_nodes[c]
                f.write(f"| `{c}` | {nd['phase']} | {nd['allowlist_rank']} | {nd['depth']} |\n")
            f.write("\n")

    print(f"  Done")
    print(f"\n=== Complete ===")
    print(f"  {len(enriched_nodes)} nodes | {len(edge_list)} edges | {len(curriculum)} groups")
    print(f"  Next: review training/corpus_admin/curriculum_manifest.md")
    print(f"  Then: build per-group corpus chunks for run 13")


if __name__ == "__main__":
    main()
