#!/usr/bin/env python3
"""Build micro-dose C17 boundary repair v3 corpora.

These corpora are intentionally much smaller than v2. The purpose is to test
whether boundary repairs can be applied without pulling the default gate below
the protected contrast checkpoint.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

IDENTITY = ROOT / "training/corpus/kernel_identity.jsonl"
OUT_DIR = ROOT / "training/corpus"
REPORT = OUT_DIR / "kernel_c17_boundary_micro_v3_report.md"
TESTS = ROOT / "training/corpus_admin/probe_sets/c17_boundary_v2.jsonl"


def prompt(user: str) -> str:
    return f"[user]{user}\n[Ninereeds]"


PAIR_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "tree",
        [
            ("what is a tree?", "A tree is a plant. A tree has a trunk, branches, and leaves."),
            ("is a tree a plant?", "Yes. A tree is a plant."),
            ("is a tree a mammal?", "No. A tree is not a mammal. A tree is a plant."),
            ("does a tree have fur?", "No. A tree does not have fur. A tree has bark and leaves."),
        ],
    ),
    (
        "plant",
        [
            ("what is a plant?", "A plant is a living thing. A plant grows."),
            ("is a plant an animal?", "No. A plant is not an animal."),
            ("is a plant a mammal?", "No. A plant is not a mammal. A mammal is an animal."),
        ],
    ),
    (
        "dog",
        [
            ("what is a dog?", "A dog is an animal. A dog is a mammal. A dog is often a pet."),
            ("what does a dog look like?", "A dog has four legs, fur, ears, a nose, and a tail."),
            ("what is the name of this dog?", "I do not know the name of this dog."),
            ("is a dog a person?", "No. A dog is not a person. A dog is an animal."),
        ],
    ),
    (
        "airport",
        [
            ("what is an airport?", "An airport is a place. Airplanes take off and land there."),
            ("what is an airport used for?", "An airport is used for airplanes to take off and land."),
            ("is an airport an airplane?", "No. An airport is not an airplane. An airport is a place."),
        ],
    ),
    (
        "airplane",
        [
            ("what is an airplane?", "An airplane is a machine and a vehicle. An airplane flies through air."),
            ("what does an airplane do?", "An airplane flies through air. It can carry people or cargo."),
            ("is an airplane a place?", "No. An airplane is not a place. An airplane is a machine."),
        ],
    ),
]

CONTRAST_ROWS = [
    ("what is a tree?", "A tree is a plant. A dog is an animal."),
    ("what is a dog?", "A dog is an animal. A tree is a plant."),
    ("what is an airport?", "An airport is a place. An airplane is a machine."),
    ("what is an airplane?", "An airplane is a machine. An airport is a place."),
    ("what happened at my school today?", "I do not know what happened at your school today."),
]


def load_jsonl(path: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                obj = json.loads(line)
                records.append({"prompt": str(obj["prompt"]), "completion": str(obj["completion"])})
    return records


def write_jsonl(path: Path, records: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def add_case_variants(records: list[dict[str, str]], user: str, answer: str) -> None:
    variants = [user]
    capitalized = user[:1].upper() + user[1:]
    if capitalized != user:
        variants.append(capitalized)
    for variant in variants:
        records.append({"prompt": prompt(variant), "completion": answer})


def build_targeted(repeats: int, identity_each_side: int) -> list[dict[str, str]]:
    identity = load_jsonl(IDENTITY)
    records = identity[:identity_each_side]
    for _ in range(repeats):
        for _concept, rows in PAIR_GROUPS:
            for user, answer in rows:
                add_case_variants(records, user, answer)
    records.extend(identity[identity_each_side : identity_each_side * 2])
    return records


def build_balanced(repeats: int, identity_each_side: int) -> list[dict[str, str]]:
    records = build_targeted(repeats, identity_each_side)
    for _ in range(repeats):
        for user, answer in CONTRAST_ROWS:
            add_case_variants(records, user, answer)
    return records


def main() -> None:
    outputs = {
        "kernel_c17_boundary_micro_v3_targeted_1x.jsonl": build_targeted(1, 24),
        "kernel_c17_boundary_micro_v3_targeted_2x.jsonl": build_targeted(2, 24),
        "kernel_c17_boundary_micro_v3_balanced_1x.jsonl": build_balanced(1, 24),
        "kernel_c17_boundary_micro_v3_balanced_2x.jsonl": build_balanced(2, 24),
    }
    lines = ["# C17 Boundary Micro V3", ""]
    for name, records in outputs.items():
        path = OUT_DIR / name
        write_jsonl(path, records)
        lines.append(f"- `{path.relative_to(ROOT)}`: {len(records)} examples")
        print(f"{path.relative_to(ROOT)} ({len(records)} examples)")
    lines.extend(
        [
            "",
            f"- boundary_tests: `{TESTS.relative_to(ROOT)}`",
            "- intent: compare lower-dose boundary repair branches from the protected contrast checkpoint",
        ]
    )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
