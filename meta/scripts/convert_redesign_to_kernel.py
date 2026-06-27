#!/usr/bin/env python3
"""Convert redesign/words dialogue files into kernel-style source files.

This does not try to invent missing facts. It preserves existing corpus content,
normalizes tags, and maps old angle names into the kernel angle families.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "training_data" / "redesign" / "words"
DEFAULT_OUTPUT = ROOT / "training_data" / "kernel_from_redesign"
DEFAULT_REPORT = ROOT / "training" / "corpus" / "kernel_from_redesign_report.md"

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


def safe_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = []
    for line in text.splitlines():
        line = line.rstrip()
        if line.strip().startswith("```"):
            continue
        line = re.sub(r"^\[(user|Ninereeds)\]\s+", r"[\1]", line)
        lines.append(line)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def valid_dialogue(text: str) -> bool:
    users = len(re.findall(r"^\[user\]", text, re.MULTILINE))
    bot = len(re.findall(r"^\[Ninereeds\]", text, re.MULTILINE))
    return users > 0 and users == bot


def split_stem(stem: str) -> tuple[str, str, bool]:
    is_rephrase = stem.endswith("_rephrase")
    if is_rephrase:
        stem = stem[: -len("_rephrase")]
    if "_" not in stem:
        return stem, "unknown", is_rephrase
    concept, angle = stem.split("_", 1)
    return concept, angle, is_rephrase


def map_angle(angle: str) -> str:
    a = angle.lower()
    if a in {"what_is", "meaning", "summary", "tell_me", "tell_me_about", "description"}:
        return "what_is"
    if any(key in a for key in ("classification", "what_kind", "kind_of", "kind")):
        return "classification"
    if any(key in a for key in ("appearance", "look", "properties", "what_can_be", "opposite")):
        return "properties"
    if any(key in a for key in ("behavior", "function", "used_for", "what_can", "what_happens", "result", "capability", "who_can")):
        return "behavior"
    if any(key in a for key in ("location", "where", "find")):
        return "location"
    if any(key in a for key in ("boundary_name", "boundary_identity", "boundary_origin", "inventor", "who_made", "who_started")):
        return "unknown_name"
    if any(key in a for key in ("boundary_internal", "boundary_feel", "boundary_feeling", "boundary_thought", "boundary_dream", "boundary_reason", "boundary_why", "boundary_cause", "boundary_when", "boundary_age", "boundary_quantity", "boundary_how_many", "boundary_extent")):
        return "unknown_internal"
    if a.startswith("boundary"):
        return "negative_category"
    if any(key in a for key in ("example", "examples")):
        return "connections"
    return "what_is"


def write_variant(out_dir: Path, angle: str, source_slug: str, content: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    base = f"{angle}.md"
    if not (out_dir / base).exists():
        path = out_dir / base
    else:
        path = out_dir / f"{angle}__{source_slug}.md"
        i = 2
        while path.exists():
            path = out_dir / f"{angle}__{source_slug}_{i}.md"
            i += 1
    path.write_text(content, encoding="utf-8")
    return path


def convert(args: argparse.Namespace) -> None:
    source = args.source if args.source.is_absolute() else ROOT / args.source
    output = args.output if args.output.is_absolute() else ROOT / args.output
    report = args.report if args.report.is_absolute() else ROOT / args.report

    if args.clean and output.exists():
        shutil.rmtree(output)

    stats = Counter()
    by_concept: dict[tuple[str, str], set[str]] = defaultdict(set)
    examples: list[str] = []

    for path in sorted(source.glob("*/*.md")):
        stats["seen"] += 1
        raw = path.read_text(encoding="utf-8", errors="replace")
        text = normalize_text(raw)
        if not valid_dialogue(text):
            stats["skipped_invalid"] += 1
            if len(examples) < 20:
                examples.append(f"- skipped `{path.relative_to(ROOT)}`: invalid tags")
            continue

        concept, old_angle, is_rephrase = split_stem(path.stem)
        category = path.parent.name
        kernel_angle = map_angle(old_angle)
        slug = safe_name(path.stem)
        if is_rephrase:
            slug += "_rephrase"
        out_dir = output / category / safe_name(concept)
        out_path = write_variant(out_dir, kernel_angle, slug, text)
        by_concept[(category, concept)].add(kernel_angle)
        stats["written"] += 1
        stats[f"angle:{kernel_angle}"] += 1
        if len(examples) < 20:
            examples.append(f"- `{path.relative_to(ROOT)}` -> `{out_path.relative_to(ROOT)}`")

    coverage = Counter()
    missing_rows: list[str] = []
    for (category, concept), angles in sorted(by_concept.items()):
        missing = sorted(REQUIRED - angles)
        coverage[len(angles & REQUIRED)] += 1
        if missing and len(missing_rows) < 200:
            missing_rows.append(
                f"- `{category}/{concept}` has {len(angles & REQUIRED)}/14; missing: {', '.join(missing)}"
            )

    lines = [
        "# Kernel From Redesign Conversion",
        "",
        f"- source: `{source}`",
        f"- output: `{output}`",
        f"- files_seen: {stats['seen']}",
        f"- files_written: {stats['written']}",
        f"- skipped_invalid: {stats['skipped_invalid']}",
        f"- concepts: {len(by_concept)}",
        "",
        "## Angle Counts",
        "",
    ]
    for key, count in sorted(stats.items()):
        if key.startswith("angle:"):
            lines.append(f"- `{key.removeprefix('angle:')}`: {count}")
    lines += ["", "## Required-Angle Coverage", ""]
    for n in sorted(coverage):
        lines.append(f"- `{n}/14`: {coverage[n]} concepts")
    lines += ["", "## Examples", "", *examples, "", "## Missing Required Angles Sample", "", *missing_rows]

    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Converted {stats['written']} files from {stats['seen']} seen")
    print(f"Concepts: {len(by_concept)}")
    print(f"Report: {report}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert redesign words to kernel-style files.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    convert(args)


if __name__ == "__main__":
    main()
