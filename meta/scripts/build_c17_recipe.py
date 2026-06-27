#!/usr/bin/env python3
"""Build C17 JSONL variants from kernel source files with recipe controls."""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter, defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TURN_RE = re.compile(r"^\[user\](.*?)\n\[Ninereeds\](.*?)(?=\n\[user\]|\Z)", re.DOTALL | re.MULTILINE)

CATEGORY_ORDER = [
    "animals",
    "people",
    "body",
    "food",
    "household",
    "places",
    "tools",
    "nature",
    "materials",
    "colors",
    "shapes",
    "quantities",
    "space",
    "time",
    "movement",
    "actions",
    "states",
    "emotions",
    "social",
    "communication",
    "cognition",
    "language",
    "properties",
    "unsorted",
]
ANGLE_ORDER = [
    "what_is",
    "classification",
    "properties",
    "behavior",
    "location",
    "connections",
    "yes_no_true",
    "yes_no_false",
    "negative_category",
    "negative_part",
    "unknown_name",
    "unknown_internal",
    "followup_known",
    "followup_unknown",
]


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def category_rank(category: str) -> int:
    try:
        return CATEGORY_ORDER.index(category)
    except ValueError:
        return len(CATEGORY_ORDER)


def angle_rank(path: Path) -> int:
    stem = path.stem.split("__", 1)[0]
    try:
        return ANGLE_ORDER.index(stem)
    except ValueError:
        return len(ANGLE_ORDER)


def safe_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def load_curriculum_order(path: Path | None) -> tuple[dict[str, int], dict[str, str]]:
    if path is None:
        return {}, {}
    full_path = path if path.is_absolute() else ROOT / path
    data = json.loads(full_path.read_text(encoding="utf-8"))
    concept_rank: dict[str, int] = {}
    concept_cluster: dict[str, str] = {}
    rank = 0
    for group in sorted(data.get("groups", []), key=lambda item: item.get("seq", 0)):
        cluster = str(group.get("cluster", ""))
        for concept in group.get("concepts", []):
            keys = {str(concept.get("canonical", ""))}
            keys.update(str(item) for item in concept.get("variants", []))
            keys.update(str(item) for item in concept.get("all_keys", []))
            for key in keys:
                normalized = safe_name(key)
                if normalized and normalized not in concept_rank:
                    concept_rank[normalized] = rank
                    concept_cluster[normalized] = cluster
            rank += 1
    return concept_rank, concept_cluster


def concept_rank(concept: str, rank_map: dict[str, int]) -> int:
    return rank_map.get(safe_name(concept), len(rank_map) + 1_000_000)


def parse_turn_examples(content: str, include_multiturn: bool) -> list[dict[str, str]]:
    examples: list[dict[str, str]] = []
    history = ""
    turns = list(TURN_RE.finditer(content.strip()))
    for idx, match in enumerate(turns):
        if idx > 0 and not include_multiturn:
            break
        user_text = match.group(1).strip()
        answer = clean_completion(match.group(2).strip())
        if not user_text or not answer:
            continue
        prompt = history + f"[user]{user_text}\n[Ninereeds]"
        examples.append({"prompt": prompt, "completion": answer})
        history = prompt + answer + "\n"
    return examples


def has_embedded_assistant(prompt: str) -> bool:
    return "[Ninereeds]" in prompt.split("\n[Ninereeds]", 1)[-1]


def clean_completion(completion: str) -> str:
    return re.sub(r"\s+response\s*$", "", completion.strip(), flags=re.IGNORECASE)


def lowercase_user_prompt(prompt: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return f"[user]{match.group(1).lower()}"

    return re.sub(r"\[user\]([^\n]*)", repl, prompt)


def iter_source_files(
    roots: list[Path],
    rank_map: dict[str, int],
    cluster_map: dict[str, str],
    max_concepts: int | None,
    order_mode: str,
) -> list[tuple[str, str, Path]]:
    grouped: dict[tuple[str, str], list[Path]] = defaultdict(list)
    for root in roots:
        full_root = root if root.is_absolute() else ROOT / root
        for path in full_root.rglob("*.md"):
            parts = path.relative_to(full_root).parts
            if len(parts) < 3:
                continue
            category, concept = parts[0], parts[1]
            rank = concept_rank(concept, rank_map)
            if max_concepts is not None and rank >= max_concepts:
                continue
            grouped[(category, concept)].append(path)

    concept_groups: list[tuple[str, str, list[Path]]] = []
    for (category, concept), paths in grouped.items():
        concept_groups.append(
            (category, concept, sorted(paths, key=lambda path: (angle_rank(path), path.name)))
        )
    concept_groups.sort(
        key=lambda item: (
            concept_rank(item[1], rank_map),
            cluster_map.get(safe_name(item[1]), ""),
            category_rank(item[0]),
            item[0],
            item[1],
        )
    )

    if order_mode in {"contrast", "contrast-angle"}:
        concept_groups = contrast_order_concepts(concept_groups, cluster_map)

    found: list[tuple[str, str, Path]] = []
    if order_mode == "contrast-angle":
        max_paths = max((len(paths) for _category, _concept, paths in concept_groups), default=0)
        for path_index in range(max_paths):
            for category, concept, paths in concept_groups:
                if path_index < len(paths):
                    found.append((category, concept, paths[path_index]))
    else:
        for category, concept, paths in concept_groups:
            for path in paths:
                found.append((category, concept, path))
    return found


def contrast_order_concepts(
    concept_groups: list[tuple[str, str, list[Path]]],
    cluster_map: dict[str, str],
) -> list[tuple[str, str, list[Path]]]:
    buckets: dict[str, deque[tuple[str, str, list[Path]]]] = defaultdict(deque)
    for category, concept, paths in concept_groups:
        key = cluster_map.get(safe_name(concept)) or f"category:{category}"
        buckets[key].append((category, concept, paths))

    ordered: list[tuple[str, str, list[Path]]] = []
    active = deque(sorted(buckets))
    while active:
        key = active.popleft()
        bucket = buckets[key]
        if not bucket:
            continue
        ordered.append(bucket.popleft())
        if bucket:
            active.append(key)
    return ordered


def build_records(
    args: argparse.Namespace,
    rank_map: dict[str, int],
    cluster_map: dict[str, str],
) -> tuple[list[dict[str, str]], Counter[str], Counter[str], Counter[str]]:
    records: list[dict[str, str]] = []
    source_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    cluster_counts: Counter[str] = Counter()
    files = iter_source_files(
        args.source_root,
        rank_map,
        cluster_map,
        args.max_concepts,
        args.order_mode,
    )
    for category, _concept, path in files:
        content = path.read_text(encoding="utf-8", errors="replace")
        parsed = parse_turn_examples(content, include_multiturn=args.include_multiturn)
        cluster = cluster_map.get(safe_name(_concept), "unranked")
        for record in parsed:
            if not args.include_multiturn and has_embedded_assistant(record["prompt"]):
                continue
            records.append(record)
            source_counts[rel(path.parents[2])] += 1
            category_counts[category] += 1
            cluster_counts[cluster] += 1
            if args.lowercase_user_copy:
                lower_prompt = lowercase_user_prompt(record["prompt"])
                if lower_prompt != record["prompt"]:
                    records.append({"prompt": lower_prompt, "completion": record["completion"]})
                    source_counts[rel(path.parents[2])] += 1
                    category_counts[category] += 1
                    cluster_counts[cluster] += 1
    return records, source_counts, category_counts, cluster_counts


def load_identity(path: Path, include_multiturn: bool) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            obj = json.loads(line)
            if "prompt" not in obj or "completion" not in obj:
                raise SystemExit(f"{rel(path)}:{line_no}: missing prompt/completion")
            prompt = str(obj["prompt"])
            completion = clean_completion(str(obj["completion"]))
            if not completion:
                continue
            if not include_multiturn and has_embedded_assistant(prompt):
                continue
            records.append({"prompt": prompt, "completion": completion})
    if not records:
        raise SystemExit(f"{rel(path)}: no identity records")
    return records


def load_extra_jsonl(path: Path, include_multiturn: bool) -> list[dict[str, str]]:
    full_path = path if path.is_absolute() else ROOT / path
    records: list[dict[str, str]] = []
    with full_path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            raw = line.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if "prompt" not in obj or "completion" not in obj:
                raise SystemExit(f"{rel(full_path)}:{line_no}: missing prompt/completion")
            prompt = str(obj["prompt"])
            completion = clean_completion(str(obj["completion"]))
            if not completion:
                continue
            if not include_multiturn and has_embedded_assistant(prompt):
                continue
            records.append({"prompt": prompt, "completion": completion})
    if not records:
        raise SystemExit(f"{rel(full_path)}: no usable records")
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


def write_jsonl(path: Path, records: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_report(
    path: Path,
    args: argparse.Namespace,
    source_counts: Counter[str],
    category_counts: Counter[str],
    cluster_counts: Counter[str],
    identity_count: int,
    identity_cycles: int,
    total: int,
    ranked_concepts: int,
) -> None:
    lines = [
        "# C17 Recipe Build",
        "",
        f"- output: `{rel(args.output)}`",
        f"- total_examples: {total}",
        f"- concept_examples: {total - identity_count}",
        f"- identity_examples: {identity_count}",
        f"- identity_share: {identity_count / total:.3%}",
        f"- identity_oversample_cycles: {identity_cycles}",
        f"- include_multiturn: {args.include_multiturn}",
        f"- lowercase_user_copy: {args.lowercase_user_copy}",
        f"- curriculum_order: `{rel(args.curriculum_order) if args.curriculum_order else ''}`",
        f"- order_mode: {args.order_mode}",
        f"- ranked_concepts: {ranked_concepts}",
        f"- seed: {args.seed}",
        "",
        "## Source Counts",
        "",
    ]
    for key in sorted(source_counts):
        lines.append(f"- {key}: {source_counts[key]}")
    lines.extend(["", "## Category Counts", ""])
    for key in sorted(category_counts, key=lambda k: (category_rank(k), k)):
        lines.append(f"- {key}: {category_counts[key]}")
    lines.extend(["", "## Cluster Counts", ""])
    for key in sorted(cluster_counts):
        lines.append(f"- {key}: {cluster_counts[key]}")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", action="append", type=Path, required=True)
    parser.add_argument("--identity-jsonl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--identity-share", type=float, default=0.12)
    parser.add_argument("--curriculum-order", type=Path)
    parser.add_argument(
        "--max-concepts",
        type=int,
        help="Keep only concepts whose curriculum rank is below this value.",
    )
    parser.add_argument(
        "--order-mode",
        choices=["curriculum", "contrast", "contrast-angle"],
        default="curriculum",
    )
    parser.add_argument(
        "--bookend-jsonl",
        action="append",
        type=Path,
        default=[],
        help="Prompt/completion JSONL to place before and after the main recipe.",
    )
    parser.add_argument("--bookend-repeat", type=int, default=1)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--include-multiturn", action="store_true")
    parser.add_argument("--lowercase-user-copy", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 0 < args.identity_share < 1:
        raise SystemExit("--identity-share must be between 0 and 1")
    rank_map, cluster_map = load_curriculum_order(args.curriculum_order)
    records, source_counts, category_counts, cluster_counts = build_records(args, rank_map, cluster_map)
    identity = load_identity(args.identity_jsonl, include_multiturn=args.include_multiturn)
    identity_needed = round(len(records) * args.identity_share / (1.0 - args.identity_share))
    identity_mixed, identity_cycles = cycle_sample(identity, identity_needed, args.seed)
    mixed = interleave(records, identity_mixed)
    bookends: list[dict[str, str]] = []
    for path in args.bookend_jsonl:
        extra = load_extra_jsonl(path, include_multiturn=args.include_multiturn)
        for _ in range(args.bookend_repeat):
            bookends.extend(extra)
    if bookends:
        mixed = bookends + mixed + bookends
    write_jsonl(args.output, mixed)
    write_report(
        args.report,
        args,
        source_counts,
        category_counts,
        cluster_counts,
        len(identity_mixed),
        identity_cycles,
        len(mixed),
        len(rank_map),
    )
    print(f"JSONL:  {rel(args.output)} ({len(mixed)} examples)")
    print(f"Report: {rel(args.report)}")


if __name__ == "__main__":
    main()
