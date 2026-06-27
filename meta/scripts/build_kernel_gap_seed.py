#!/usr/bin/env python3
"""Build seed JSONL for missing kernel angles after redesign conversion."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = {
    "what_is",
    "classification",
    "properties",
    "behavior",
    "location",
    "connections",
    "negative_category",
    "negative_part",
    "yes_no_true",
    "yes_no_false",
    "unknown_name",
    "unknown_internal",
    "followup_known",
    "followup_unknown",
}


def file_angle(path: Path) -> str:
    return path.stem.split("__", 1)[0]


def safe_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build missing-angle seed JSONL.")
    parser.add_argument("--words-file", type=Path, default=ROOT / "training" / "corpus_admin" / "kernel" / "kernel_full_words.jsonl")
    parser.add_argument("--source-root", type=Path, default=ROOT / "training_data" / "kernel_from_redesign")
    parser.add_argument("--output", type=Path, default=ROOT / "training" / "corpus_admin" / "kernel" / "kernel_gap_words.jsonl")
    parser.add_argument("--max-missing", type=int, default=14, help="Include concepts with at most this many missing angles.")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    words_file = args.words_file if args.words_file.is_absolute() else ROOT / args.words_file
    source_root = args.source_root if args.source_root.is_absolute() else ROOT / args.source_root
    output = args.output if args.output.is_absolute() else ROOT / args.output

    records = [json.loads(line) for line in words_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    out_records = []
    for record in records:
        category = record.get("category", "unsorted")
        concept = record["concept_id"]
        concept_dir = source_root / category / safe_name(str(concept))
        existing = set()
        if concept_dir.exists():
            existing = {file_angle(path) for path in concept_dir.glob("*.md")}
        missing = sorted(REQUIRED - existing)
        if not missing or len(missing) > args.max_missing:
            continue
        new_record = dict(record)
        new_record["existing_angles"] = sorted(existing)
        new_record["missing_angles"] = missing
        new_record["generation_mode"] = "fill_missing_kernel_angles"
        out_records.append(new_record)
        if args.limit and len(out_records) >= args.limit:
            break

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in out_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote {len(out_records)} gap records -> {output}")


if __name__ == "__main__":
    main()
