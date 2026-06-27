#!/usr/bin/env python3
"""Build a full-vocabulary seed list for kernel-style corpus generation."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ALLOWLIST = ROOT / "inventory" / "allowlist.txt"
DEFAULT_REDESIGN_WORDS = ROOT / "training_data" / "redesign" / "words"
DEFAULT_OUTPUT = ROOT / "training" / "corpus_admin" / "kernel" / "kernel_full_words.jsonl"


def safe_concept(value: str) -> str:
    return value.strip()


def concept_from_stem(stem: str) -> str:
    if stem.endswith("_rephrase"):
        stem = stem[: -len("_rephrase")]
    return stem.split("_", 1)[0]


def build_bucket_index(words_dir: Path) -> dict[str, str]:
    buckets: dict[str, Counter[str]] = defaultdict(Counter)
    if not words_dir.exists():
        return {}
    for path in words_dir.glob("*/*.md"):
        concept = concept_from_stem(path.stem)
        if concept:
            buckets[concept][path.parent.name] += 1
    return {concept: counts.most_common(1)[0][0] for concept, counts in buckets.items()}


def guess_kind(word: str, category: str) -> str:
    if category in {"actions", "movement", "communication", "processes"}:
        return "verb"
    if category in {"properties", "colors", "states"}:
        return "adjective"
    if category in {"time", "space", "quantities", "cognition", "emotions", "social", "language"}:
        return "abstract"
    if re.search(r"(ing|ed)$", word) and category == "actions":
        return "verb"
    return "concrete_noun"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build full kernel vocabulary seed JSONL.")
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    parser.add_argument("--redesign-words", type=Path, default=DEFAULT_REDESIGN_WORDS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    bucket_index = build_bucket_index(args.redesign_words)
    words = [
        safe_concept(line)
        for line in args.allowlist.read_text(encoding="utf-8").splitlines()
        if safe_concept(line)
    ]
    if args.limit:
        words = words[: args.limit]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for word in words:
            category = bucket_index.get(word, "unsorted")
            record = {
                "concept_id": word,
                "category": category,
                "kind": guess_kind(word, category),
                "source": "inventory/allowlist.txt",
                "generation_mode": "infer_simple_facts",
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    categories = Counter(bucket_index.get(word, "unsorted") for word in words)
    print(f"Wrote {len(words)} records -> {args.output}")
    for category, count in categories.most_common():
        print(f"{category:14s} {count}")


if __name__ == "__main__":
    main()
