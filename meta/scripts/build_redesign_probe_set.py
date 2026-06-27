#!/usr/bin/env python3
"""
Build trace-ready probe sets from training_data/redesign/.

The redesign corpus is generated as many small angle files:

  training_data/redesign/words/<bucket>/<concept>_<angle>.md
  training_data/redesign/words/<bucket>/<concept>_<angle>_rephrase.md

This script samples those files into a balanced JSONL probe set with the metadata
required by brain_map.py trace.
"""
from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REDESIGN = ROOT / "training_data" / "redesign"
WORDS = REDESIGN / "words"
IDENTITY = REDESIGN / "identity"
DEFAULT_OUT = ROOT / "training" / "corpus_admin" / "probe_sets" / "redesign_current.jsonl"

# Longest suffix wins. Keep this list explicit so concept names may contain underscores.
KNOWN_ANGLES = [
    "what_can_you_tell_me_about",
    "what_can_you_tell_me",
    "what_can_you_tell",
    "what_is_it_used_for",
    "where_do_you_find_it",
    "what_does_someone_do",
    "what_does_it_mean",
    "what_does_it_do",
    "what_happens_when",
    "what_is_activating",
    "what_can_be_activated",
    "what_kind_of_thing",
    "what_can_be",
    "what_happens",
    "what_kind",
    "what_can",
    "what_for",
    "what_is",
    "tell_me_about",
    "tell_me",
    "boundary_speculative",
    "boundary_appearance",
    "boundary_visibility",
    "boundary_invention",
    "boundary_internal",
    "boundary_quantity",
    "boundary_identity",
    "boundary_feelings",
    "boundary_feeling",
    "boundary_history",
    "boundary_inventor",
    "boundary_origin",
    "boundary_purpose",
    "boundary_measure",
    "boundary_reason",
    "boundary_degree",
    "boundary_count",
    "boundary_cause",
    "boundary_when",
    "boundary_name",
    "boundary_why",
    "boundary_who",
    "boundary_age",
    "boundary_feel",
    "classification",
    "capability",
    "appearance",
    "behavior",
    "function",
    "location",
    "opposite",
    "examples",
    "example",
    "meaning",
    "summary",
    "general",
    "result",
    "where",
    "about",
    "kind",
    "kinds",
    "happens",
    "who_can",
    "can_do",
    "gerund",
]

PREFERRED_ANGLES = [
    "what_is",
    "meaning",
    "example",
    "examples",
    "appearance",
    "function",
    "location",
    "behavior",
    "classification",
    "opposite",
    "what_can",
    "what_happens",
    "tell_me",
    "tell_me_about",
    "boundary_internal",
    "boundary_name",
    "boundary_quantity",
    "boundary_reason",
    "boundary_why",
    "boundary_origin",
]


@dataclass(frozen=True)
class Candidate:
    path: Path
    bucket: str
    concept_id: str
    angle: str
    is_rephrase: bool
    prompt: str


def first_user_prompt(path: Path) -> str | None:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("[user]"):
            return line.strip()
    return None


def split_name(path: Path) -> tuple[str, str, bool]:
    stem = path.stem
    is_rephrase = stem.endswith("_rephrase")
    if is_rephrase:
        stem = stem[: -len("_rephrase")]
    for angle in sorted(KNOWN_ANGLES, key=len, reverse=True):
        suffix = "_" + angle
        if stem.endswith(suffix):
            concept = stem[: -len(suffix)]
            return concept, angle, is_rephrase
    parts = stem.rsplit("_", 1)
    if len(parts) == 2:
        return parts[0], parts[1], is_rephrase
    return stem, "unknown", is_rephrase


def probe_role(angle: str, bucket: str) -> str:
    if angle.startswith("boundary_"):
        return "unknown_boundary"
    if angle in {"what_is", "meaning", "about", "tell_me", "tell_me_about", "summary", "general"}:
        return "definition"
    if angle in {"example", "examples"}:
        return "example"
    if angle in {"appearance", "location", "function", "behavior", "classification", "opposite", "capability", "what_can", "what_happens"}:
        return angle
    if bucket == "identity":
        return "self_identity"
    return "angle_probe"


def expected_behavior(candidate: Candidate) -> str:
    if candidate.bucket == "identity":
        return "answer identity or capability questions about Ninereeds"
    if candidate.angle.startswith("boundary_"):
        return (
            f"decline unknowable or out-of-scope information about "
            f"{candidate.concept_id}; expected activation cluster: {candidate.bucket}"
        )
    return f"answer about {candidate.concept_id}; expected activation cluster: {candidate.bucket}"


def to_record(candidate: Candidate, sequence: int) -> dict:
    suffix = "_r" if candidate.is_rephrase else ""
    probe_id = (
        f"redesign_{candidate.bucket}_{candidate.concept_id}_"
        f"{candidate.angle}{suffix}_{sequence:04d}"
    )
    return {
        "id": probe_id,
        "campaign": "redesign",
        "category": candidate.bucket,
        "lang": "EN",
        "language": "EN",
        "concept_id": candidate.concept_id,
        "template_id": candidate.angle + ("_rephrase" if candidate.is_rephrase else ""),
        "probe_role": probe_role(candidate.angle, candidate.bucket),
        "construction_id": candidate.angle,
        "source_corpus": str(candidate.path.relative_to(ROOT)),
        "prompt": candidate.prompt,
        "expected_cluster": candidate.bucket,
        "expected_behavior": expected_behavior(candidate),
    }


def load_candidates(include_rephrases: bool) -> list[Candidate]:
    candidates: list[Candidate] = []
    for path in sorted(WORDS.glob("*/*.md")):
        concept, angle, is_rephrase = split_name(path)
        if is_rephrase and not include_rephrases:
            continue
        prompt = first_user_prompt(path)
        if not prompt:
            continue
        candidates.append(Candidate(path, path.parent.name, concept, angle, is_rephrase, prompt))
    return candidates


def load_identity_candidates() -> list[Candidate]:
    candidates: list[Candidate] = []
    for path in sorted(IDENTITY.glob("*.md")):
        prompt = first_user_prompt(path)
        if not prompt:
            continue
        concept, angle, _ = split_name(path)
        candidates.append(Candidate(path, "identity", concept, angle, False, prompt))
    return candidates


def angle_rank(angle: str) -> int:
    try:
        return PREFERRED_ANGLES.index(angle)
    except ValueError:
        return len(PREFERRED_ANGLES)


def select_balanced(candidates: list[Candidate], concepts_per_bucket: int,
                    angles_per_concept: int, seed: int,
                    allow_other_angles: bool) -> list[Candidate]:
    rng = random.Random(seed)
    by_bucket: dict[str, dict[str, list[Candidate]]] = defaultdict(lambda: defaultdict(list))
    preferred = set(PREFERRED_ANGLES)
    for candidate in candidates:
        if not allow_other_angles and candidate.angle not in preferred:
            continue
        by_bucket[candidate.bucket][candidate.concept_id].append(candidate)

    selected: list[Candidate] = []
    for bucket in sorted(by_bucket):
        concepts = [
            concept for concept, rows in by_bucket[bucket].items()
            if any(row.angle in preferred for row in rows)
        ]
        rng.shuffle(concepts)
        concepts = sorted(concepts[:concepts_per_bucket])
        for concept in concepts:
            rows = sorted(
                by_bucket[bucket][concept],
                key=lambda c: (angle_rank(c.angle), c.is_rephrase, c.angle, str(c.path)),
            )
            selected.extend(rows[:angles_per_concept])
    return selected


def write_jsonl(path: Path, records: list[dict]) -> None:
    header = [
        "# Probe set: redesign current corpus",
        "# Generated by: meta/scripts/build_redesign_probe_set.py",
        "# Source: training_data/redesign/identity + training_data/redesign/words",
        "# Format: trace-ready JSONL for brain_map.py",
        "",
    ]
    lines = header + [json.dumps(record, ensure_ascii=False, separators=(",", ": ")) for record in records]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a balanced redesign probe set.")
    ap.add_argument("--output", default=str(DEFAULT_OUT))
    ap.add_argument("--concepts-per-bucket", type=int, default=6)
    ap.add_argument("--angles-per-concept", type=int, default=4)
    ap.add_argument("--identity-limit", type=int, default=12)
    ap.add_argument("--include-rephrases", action="store_true")
    ap.add_argument("--allow-other-angles", action="store_true",
                    help="Include unusual filename angles outside the preferred probe families")
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    candidates = load_candidates(include_rephrases=args.include_rephrases)
    selected = select_balanced(
        candidates,
        concepts_per_bucket=args.concepts_per_bucket,
        angles_per_concept=args.angles_per_concept,
        seed=args.seed,
        allow_other_angles=args.allow_other_angles,
    )
    identity = load_identity_candidates()[: args.identity_limit]
    all_selected = identity + selected
    records = [to_record(candidate, i + 1) for i, candidate in enumerate(all_selected)]
    write_jsonl(Path(args.output), records)

    buckets = sorted({candidate.bucket for candidate in selected})
    print(f"Wrote {len(records)} probes to {args.output}")
    print(f"Identity probes: {len(identity)}")
    print(f"Word buckets: {len(buckets)}")
    print(f"Word probes: {len(selected)}")


if __name__ == "__main__":
    main()
