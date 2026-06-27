#!/usr/bin/env python3
"""Build low-dose balanced C17 boundary repair v2 corpora."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

BASE_CONTRAST = ROOT / "training/corpus/kernel_c17_contrast_angle_1200_e1.jsonl"
IDENTITY = ROOT / "training/corpus/kernel_identity.jsonl"
REPAIR = ROOT / "training/corpus/kernel_c17_boundary_repair_v2.jsonl"
DAMAGED = ROOT / "training/corpus/kernel_c17_damaged_concepts_v2.jsonl"
REVIEW = ROOT / "training/corpus/kernel_c17_contrast_review_repair_v2.jsonl"
REPORT = ROOT / "training/corpus/kernel_c17_boundary_repair_v2_report.md"
TESTS = ROOT / "training/corpus_admin/probe_sets/c17_boundary_v2.jsonl"


def prompt(user: str) -> str:
    return f"[user]{user}\n[Ninereeds]"


PAIR_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "tree",
        [
            ("what is a tree?", "A tree is a plant. A tree has a trunk, branches, and leaves."),
            ("what kind of thing is a tree?", "A tree is a plant. A tree is a living thing. A tree is bigger than a bush."),
            ("what does a tree look like?", "A tree has a trunk. A tree has branches. A tree has leaves. A tree is often tall."),
            ("is a tree a plant?", "Yes. A tree is a plant."),
            ("is a tree an animal?", "No. A tree is not an animal. A tree is a plant."),
            ("is a tree a mammal?", "No. A tree is not a mammal. A tree is a plant."),
            ("does a tree have fur?", "No. A tree does not have fur. A tree has bark, branches, and leaves."),
        ],
    ),
    (
        "plant",
        [
            ("what is a plant?", "A plant is a living thing. A plant grows. A plant needs water, sunlight, and air."),
            ("what kind of thing is a plant?", "A plant is a living thing. A tree is a kind of plant."),
            ("is a plant an animal?", "No. A plant is not an animal. A plant is a living thing that grows."),
            ("is a plant a mammal?", "No. A plant is not a mammal. A mammal is an animal."),
            ("does a plant have fur?", "No. A plant does not have fur. Some plants have leaves, stems, roots, flowers, or bark."),
        ],
    ),
    (
        "dog",
        [
            ("what is a dog?", "A dog is an animal. A dog is a mammal. A dog is often a pet. A dog has four legs and fur."),
            ("what does a dog look like?", "A dog has four legs. A dog has fur. A dog has ears, a nose, and a tail."),
            ("what kind of thing is a dog?", "A dog is an animal. A dog is a mammal. A dog is often a pet."),
            ("is a dog a person?", "No. A dog is not a person. A dog is an animal."),
            ("is a dog a plant?", "No. A dog is not a plant. A dog is an animal."),
            ("what is the name of this dog?", "I do not know the name of this dog. I only know that a dog is an animal."),
        ],
    ),
    (
        "airport",
        [
            ("what is an airport?", "An airport is a place. Airplanes take off and land at an airport. An airport has runways."),
            ("what is an airport used for?", "An airport is used for airplanes to take off and land. An airport is used for travel and cargo."),
            ("is an airport an airplane?", "No. An airport is not an airplane. An airport is a place."),
            ("is an airport an animal?", "No. An airport is not an animal. An airport is a place."),
        ],
    ),
    (
        "airplane",
        [
            ("what is an airplane?", "An airplane is a machine. An airplane is a vehicle. An airplane flies through air."),
            ("what does an airplane do?", "An airplane flies through air. An airplane can carry people or cargo. An airplane can take off and land."),
            ("how does an airplane work?", "An airplane uses wings and engines to move through air. Engines push the airplane forward."),
            ("is an airplane an animal?", "No. An airplane is not an animal. An airplane is a machine and a vehicle."),
            ("is an airplane a place?", "No. An airplane is not a place. An airplane is a machine and a vehicle."),
        ],
    ),
]

CONTRAST_ROWS = [
    ("what is a tree?", "A tree is a plant. A tree has a trunk, branches, and leaves."),
    ("what is a dog?", "A dog is an animal. A dog is a mammal. A dog has four legs and fur."),
    ("what is an airport?", "An airport is a place. Airplanes take off and land at an airport."),
    ("what is an airplane?", "An airplane is a machine and a vehicle. An airplane flies through air."),
    ("is a tree a mammal?", "No. A tree is not a mammal. A tree is a plant."),
    ("is a plant an animal?", "No. A plant is not an animal. A plant is a living thing."),
    ("what is the name of this dog?", "I do not know the name of this dog. I only know that a dog is an animal."),
    ("what happened at my school today?", "I do not know what happened at your school today."),
]

TEST_ITEMS = [
    {
        "id": "tree_definition",
        "concept_id": "tree",
        "category": "nature",
        "prompt": prompt("what is a tree?"),
        "required_any": [["plant"], ["trunk"], ["branches", "leaves"]],
        "forbidden_any": ["is an animal", "is a mammal", "tree is an animal", "tree is a mammal"],
    },
    {
        "id": "tree_not_mammal",
        "concept_id": "tree",
        "category": "nature",
        "prompt": prompt("is a tree a mammal?"),
        "required_any": [["no"], ["not a mammal"], ["plant"]],
        "forbidden_any": ["yes", "tree is a mammal"],
    },
    {
        "id": "plant_not_animal",
        "concept_id": "plant",
        "category": "nature",
        "prompt": prompt("is a plant an animal?"),
        "required_any": [["no"], ["not an animal"], ["plant"]],
        "forbidden_any": ["yes", "plant is an animal", "mammal"],
    },
    {
        "id": "dog_definition_full",
        "concept_id": "dog",
        "category": "animals",
        "prompt": prompt("what is a dog?"),
        "required_any": [["animal"], ["mammal", "pet"], ["four legs", "fur"]],
        "forbidden_any": ["plant", "person who"],
    },
    {
        "id": "dog_name_boundary",
        "concept_id": "dog",
        "category": "animals",
        "prompt": prompt("what is the name of this dog?"),
        "required_any": [["i do not know", "don't know"], ["dog"], ["animal"]],
        "forbidden_any": ["person", "plant"],
    },
    {
        "id": "airport_function_full",
        "concept_id": "airport",
        "category": "places",
        "prompt": prompt("what is an airport used for?"),
        "required_any": [["airplane", "airplanes"], ["take off", "land"], ["travel", "cargo"]],
        "forbidden_any": ["animal", "plant", "person who"],
    },
    {
        "id": "airplane_function_full",
        "concept_id": "airplane",
        "category": "tools",
        "prompt": prompt("what does an airplane do?"),
        "required_any": [["fly", "flies"], ["air"], ["take off", "land"], ["people", "cargo"]],
        "forbidden_any": ["animal", "plant", "person who"],
    },
]


def write_jsonl(path: Path, records: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                obj = json.loads(line)
                records.append({"prompt": str(obj["prompt"]), "completion": str(obj["completion"])})
    return records


def add_case_variants(records: list[dict[str, str]], user: str, answer: str) -> None:
    variants = [user]
    cap = user[:1].upper() + user[1:]
    if cap != user:
        variants.append(cap)
    for variant in variants:
        records.append({"prompt": prompt(variant), "completion": answer})


def main() -> None:
    repair: list[dict[str, str]] = []
    damaged: list[dict[str, str]] = []
    counts: Counter[str] = Counter()

    identity = load_jsonl(IDENTITY)
    repair.extend(identity[:80])

    for _ in range(4):
        for concept, rows in PAIR_GROUPS:
            for user, answer in rows:
                add_case_variants(repair, user, answer)
                add_case_variants(damaged, user, answer)
                counts[concept] += 2
        for user, answer in CONTRAST_ROWS:
            add_case_variants(repair, user, answer)
            counts["contrast"] += 2

    # A second, tighter damaged-concepts corpus for a controlled one-epoch test.
    for _ in range(8):
        for concept, rows in PAIR_GROUPS:
            for user, answer in rows:
                add_case_variants(damaged, user, answer)

    repair.extend(identity[80:140])
    write_jsonl(REPAIR, repair)
    write_jsonl(DAMAGED, damaged)

    base = load_jsonl(BASE_CONTRAST)
    review: list[dict[str, str]] = []
    repair_i = 0
    for i, row in enumerate(base, start=1):
        review.append(row)
        if i % 96 == 0 and repair_i < len(repair):
            review.append(repair[repair_i])
            repair_i += 1
    while repair_i < len(repair):
        review.append(repair[repair_i])
        repair_i += 1
    write_jsonl(REVIEW, review)

    TESTS.parent.mkdir(parents=True, exist_ok=True)
    with TESTS.open("w", encoding="utf-8") as handle:
        for item in TEST_ITEMS:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    lines = [
        "# C17 Boundary Repair V2",
        "",
        f"- repair_output: `{REPAIR.relative_to(ROOT)}`",
        f"- repair_examples: {len(repair)}",
        f"- damaged_output: `{DAMAGED.relative_to(ROOT)}`",
        f"- damaged_examples: {len(damaged)}",
        f"- review_output: `{REVIEW.relative_to(ROOT)}`",
        f"- review_examples: {len(review)}",
        f"- base_contrast_examples: {len(base)}",
        f"- boundary_tests: `{TESTS.relative_to(ROOT)}`",
        "",
        "## Counts",
        "",
    ]
    for key in sorted(counts):
        lines.append(f"- {key}: {counts[key]}")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"repair: {REPAIR.relative_to(ROOT)} ({len(repair)} examples)")
    print(f"damaged: {DAMAGED.relative_to(ROOT)} ({len(damaged)} examples)")
    print(f"review: {REVIEW.relative_to(ROOT)} ({len(review)} examples)")
    print(f"tests: {TESTS.relative_to(ROOT)} ({len(TEST_ITEMS)} tests)")


if __name__ == "__main__":
    main()
