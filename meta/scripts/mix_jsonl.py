#!/usr/bin/env python3
"""Build a fixed-ratio mixed training JSONL from prompt/completion files."""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_prompt_completion(path: Path, label: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{rel(path)}:{line_no}: invalid JSON: {exc}") from exc

            if not isinstance(obj, dict):
                raise SystemExit(f"{rel(path)}:{line_no}: expected JSON object")
            if "prompt" not in obj or "completion" not in obj:
                raise SystemExit(f"{rel(path)}:{line_no}: missing prompt/completion fields")

            prompt = str(obj["prompt"])
            completion = str(obj["completion"])
            if not prompt or not completion:
                continue
            if "[Ninereeds]" not in prompt:
                raise SystemExit(f"{rel(path)}:{line_no}: prompt is missing [Ninereeds] tag")

            records.append({"prompt": prompt, "completion": completion, "_source": label})

    if not records:
        raise SystemExit(f"{rel(path)}: no usable records")
    return records


def cycle_sample(records: list[dict[str, str]], size: int, seed: int) -> tuple[list[dict[str, str]], int]:
    rng = random.Random(seed)
    out: list[dict[str, str]] = []
    cycles = 0
    while len(out) < size:
        batch = list(records)
        rng.shuffle(batch)
        out.extend(batch)
        cycles += 1
    return out[:size], cycles


def interleave(primary: list[dict[str, str]], inserted: list[dict[str, str]]) -> list[dict[str, str]]:
    """Evenly spread inserted records through primary while preserving primary order."""
    total = len(primary) + len(inserted)
    mixed: list[dict[str, str]] = []
    p_i = 0
    i_i = 0
    for pos in range(total):
        target_inserted = ((pos + 1) * len(inserted)) // total
        if i_i < target_inserted:
            mixed.append(inserted[i_i])
            i_i += 1
        else:
            mixed.append(primary[p_i])
            p_i += 1
    return mixed


def write_jsonl(path: Path, records: Iterable[dict[str, str]]) -> int:
    count = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            clean = {"prompt": record["prompt"], "completion": record["completion"]}
            handle.write(json.dumps(clean, ensure_ascii=False) + "\n")
            count += 1
    return count


def write_report(
    path: Path,
    output: Path,
    input_counts: Counter[str],
    output_counts: Counter[str],
    identity_target: float,
    identity_cycles: int,
    seed: int,
) -> None:
    total = sum(output_counts.values())
    identity_share = output_counts["identity"] / total if total else 0.0
    lines = [
        "# C17 Mixed JSONL Build",
        "",
        f"- output: `{rel(output)}`",
        f"- total_examples: {total}",
        f"- identity_target_share: {identity_target:.3f}",
        f"- identity_actual_share: {identity_share:.3f}",
        f"- identity_oversample_cycles: {identity_cycles}",
        f"- seed: {seed}",
        "",
        "## Input counts",
        "",
    ]
    for key in sorted(input_counts):
        lines.append(f"- {key}: {input_counts[key]}")
    lines.extend(["", "## Output counts", ""])
    for key in sorted(output_counts):
        share = output_counts[key] / total if total else 0.0
        lines.append(f"- {key}: {output_counts[key]} ({share:.3%})")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--concept-jsonl",
        action="append",
        type=Path,
        required=True,
        help="Concept/relation JSONL input. May be passed multiple times.",
    )
    parser.add_argument("--identity-jsonl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--identity-share", type=float, default=0.12)
    parser.add_argument("--seed", type=int, default=1337)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 0 < args.identity_share < 1:
        raise SystemExit("--identity-share must be between 0 and 1")

    concept_records: list[dict[str, str]] = []
    input_counts: Counter[str] = Counter()
    for path in args.concept_jsonl:
        label = path.stem
        records = load_prompt_completion(path, label)
        concept_records.extend(records)
        input_counts[label] += len(records)

    identity_records = load_prompt_completion(args.identity_jsonl, "identity")
    input_counts["identity"] = len(identity_records)

    identity_needed = round(len(concept_records) * args.identity_share / (1.0 - args.identity_share))
    identity_mixed, identity_cycles = cycle_sample(identity_records, identity_needed, args.seed)
    mixed = interleave(concept_records, identity_mixed)

    written = write_jsonl(args.output, mixed)
    output_counts: Counter[str] = Counter(record["_source"] for record in mixed)
    if written != sum(output_counts.values()):
        raise SystemExit("internal count mismatch while writing mixed JSONL")

    write_report(
        args.report,
        args.output,
        input_counts,
        output_counts,
        args.identity_share,
        identity_cycles,
        args.seed,
    )
    print(f"JSONL:  {rel(args.output)} ({written} examples)")
    print(f"Report: {rel(args.report)}")


if __name__ == "__main__":
    main()
