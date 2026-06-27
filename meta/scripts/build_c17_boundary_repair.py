#!/usr/bin/env python3
"""Build targeted C17 boundary repair and contrast-review corpora."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REPAIR = ROOT / "training/corpus/kernel_c17_boundary_repair.jsonl"
REVIEW = ROOT / "training/corpus/kernel_c17_contrast_review_repair.jsonl"
REPORT = ROOT / "training/corpus/kernel_c17_boundary_repair_report.md"
TESTS = ROOT / "training/corpus_admin/probe_sets/c17_boundary.jsonl"
BASE_CONTRAST = ROOT / "training/corpus/kernel_c17_contrast_angle_1200_e1.jsonl"
IDENTITY = ROOT / "training/corpus/kernel_identity.jsonl"


def prompt(user: str) -> str:
    return f"[user]{user}\n[Ninereeds]"


BASE_EXAMPLES: list[tuple[str, str, str]] = [
    ("tree", "what is a tree?", "A tree is a plant. A tree has a trunk, branches, and leaves. A tree is not an animal."),
    ("tree", "what kind of thing is a tree?", "A tree is a plant. A tree is a living thing. A tree is not a mammal."),
    ("tree", "what does a tree look like?", "A tree has a trunk. A tree has branches. A tree has leaves. A tree is often tall."),
    ("tree", "is a tree an animal?", "No. A tree is not an animal. A tree is a plant."),
    ("tree", "is a tree a mammal?", "No. A tree is not a mammal. A tree is a plant."),
    ("tree", "is a tree a person?", "No. A tree is not a person. A tree is a plant."),
    ("tree", "is a tree a plant?", "Yes. A tree is a plant. A tree is a living thing."),
    ("tree", "does a tree have fur?", "No. A tree does not have fur. A tree has bark, branches, and leaves."),
    ("tree", "does a tree have leaves?", "Yes. A tree has leaves. A tree also has a trunk and branches."),
    ("plant", "what is a plant?", "A plant is a living thing. A plant grows. A plant needs water, sunlight, and air. A plant is not an animal."),
    ("plant", "what kind of thing is a plant?", "A plant is a living thing. A plant is not an animal. A tree is a kind of plant."),
    ("plant", "is a plant an animal?", "No. A plant is not an animal. A plant is a living thing that grows."),
    ("plant", "is a plant a mammal?", "No. A plant is not a mammal. A mammal is an animal."),
    ("plant", "is a plant a person?", "No. A plant is not a person. A plant is a living thing."),
    ("plant", "does a plant have fur?", "No. A plant does not have fur. Some plants have leaves, stems, roots, flowers, or bark."),
    ("animal", "what is an animal?", "An animal is a living thing. An animal can move and eat food. An animal is not a plant."),
    ("animal", "is an animal a plant?", "No. An animal is not a plant. Animals and plants are different kinds of living things."),
    ("animal", "is an animal a living thing?", "Yes. An animal is a living thing."),
    ("mammal", "what is a mammal?", "A mammal is a type of animal. A mammal has hair or fur. A mammal feeds milk to its babies."),
    ("mammal", "is a mammal a plant?", "No. A mammal is not a plant. A mammal is an animal."),
    ("mammal", "is a mammal an animal?", "Yes. A mammal is an animal."),
    ("dog", "what is a dog?", "A dog is an animal. A dog is a mammal. A dog is often a pet. A dog is not a person."),
    ("dog", "is a dog a person?", "No. A dog is not a person. A dog is an animal."),
    ("dog", "is a dog a plant?", "No. A dog is not a plant. A dog is an animal."),
    ("dog", "what is the name of this dog?", "I do not know the name of this dog. I only know that a dog is an animal."),
    ("dog", "what is the name of that dog?", "I do not know the name of that dog. I only know that a dog is an animal."),
    ("person", "what is a person?", "A person is a human being. A person is not a dog. A person is not a plant."),
    ("person", "is a person a dog?", "No. A person is not a dog. A person is a human being."),
    ("airport", "what is an airport?", "An airport is a place. Airplanes take off and land at an airport. An airport is not an airplane."),
    ("airport", "what is an airport used for?", "An airport is used for airplanes to take off and land. An airport is used for travel and cargo."),
    ("airport", "is an airport an airplane?", "No. An airport is not an airplane. An airport is a place."),
    ("airport", "is an airport an animal?", "No. An airport is not an animal. An airport is a place."),
    ("airplane", "what is an airplane?", "An airplane is a machine. An airplane is a vehicle. An airplane flies through air."),
    ("airplane", "what does an airplane do?", "An airplane flies through air. An airplane can carry people or cargo. An airplane can take off and land."),
    ("airplane", "how does an airplane work?", "An airplane uses wings and engines to move through air. Engines push the airplane forward."),
    ("airplane", "is an airplane an animal?", "No. An airplane is not an animal. An airplane is a machine and a vehicle."),
    ("airplane", "is an airplane a place?", "No. An airplane is not a place. An airplane is a machine and a vehicle."),
]

CONTRAST_SETS = [
    [
        ("what is a tree?", "A tree is a plant. A tree is not an animal."),
        ("what is a dog?", "A dog is an animal. A dog is not a plant."),
        ("what is an airport?", "An airport is a place. An airport is not an airplane."),
        ("what is an airplane?", "An airplane is a machine and a vehicle. An airplane is not an animal."),
    ],
    [
        ("is a tree a mammal?", "No. A tree is not a mammal. A tree is a plant."),
        ("is a dog a mammal?", "Yes. A dog is a mammal. A dog is an animal."),
        ("is a plant an animal?", "No. A plant is not an animal."),
        ("is a person a dog?", "No. A person is not a dog. A person is a human being."),
    ],
    [
        ("what is the name of this dog?", "I do not know the name of this dog. I only know that a dog is an animal."),
        ("what happened at my school today?", "I do not know what happened at your school today."),
        ("what is a tree?", "A tree is a plant. A tree has a trunk, branches, and leaves."),
        ("what does an airplane do?", "An airplane flies through air. An airplane can take off and land."),
    ],
]

TEST_ITEMS = [
    {
        "id": "tree_definition",
        "concept_id": "tree",
        "category": "nature",
        "prompt": prompt("what is a tree?"),
        "required_any": [["plant"], ["trunk"], ["branches", "leaves"]],
        "forbidden_any": ["mammal", "animal", "person"],
    },
    {
        "id": "tree_not_mammal",
        "concept_id": "tree",
        "category": "nature",
        "prompt": prompt("is a tree a mammal?"),
        "required_any": [["no"], ["not a mammal"], ["plant"]],
        "forbidden_any": ["yes"],
    },
    {
        "id": "plant_not_animal",
        "concept_id": "plant",
        "category": "nature",
        "prompt": prompt("is a plant an animal?"),
        "required_any": [["no"], ["not an animal"], ["plant"]],
        "forbidden_any": ["yes", "mammal"],
    },
    {
        "id": "dog_name_boundary",
        "concept_id": "dog",
        "category": "animals",
        "prompt": prompt("what is the name of this dog?"),
        "required_any": [["i do not know", "don't know"], ["dog"], ["animal"]],
        "forbidden_any": ["person", "plant", "mammal's name"],
    },
    {
        "id": "airport_not_airplane",
        "concept_id": "airport",
        "category": "places",
        "prompt": prompt("is an airport an airplane?"),
        "required_any": [["no"], ["not an airplane"], ["place"]],
        "forbidden_any": ["yes", "animal"],
    },
    {
        "id": "airplane_function",
        "concept_id": "airplane",
        "category": "tools",
        "prompt": prompt("what does an airplane do?"),
        "required_any": [["fly", "flies"], ["air"], ["take off", "land"]],
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


def main() -> None:
    repair: list[dict[str, str]] = []
    counts: Counter[str] = Counter()
    for repeat in range(24):
        for concept, user, answer in BASE_EXAMPLES:
            repair.append({"prompt": prompt(user), "completion": answer})
            counts[concept] += 1
            capitalized = user[:1].upper() + user[1:]
            if capitalized != user:
                repair.append({"prompt": prompt(capitalized), "completion": answer})
                counts[concept] += 1
        for contrast_set in CONTRAST_SETS:
            for user, answer in contrast_set:
                repair.append({"prompt": prompt(user), "completion": answer})
                counts["contrast"] += 1

    identity = load_jsonl(IDENTITY)
    # Keep identity pressure present without making this a broad identity run.
    repair = identity[:160] + repair + identity[160:320] + repair[:320]
    write_jsonl(REPAIR, repair)

    base = load_jsonl(BASE_CONTRAST)
    review = repair + base + repair
    write_jsonl(REVIEW, review)

    TESTS.parent.mkdir(parents=True, exist_ok=True)
    with TESTS.open("w", encoding="utf-8") as handle:
        for item in TEST_ITEMS:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    lines = [
        "# C17 Boundary Repair",
        "",
        f"- repair_output: `{REPAIR.relative_to(ROOT)}`",
        f"- repair_examples: {len(repair)}",
        f"- review_output: `{REVIEW.relative_to(ROOT)}`",
        f"- review_examples: {len(review)}",
        f"- base_contrast_examples: {len(base)}",
        f"- boundary_tests: `{TESTS.relative_to(ROOT)}`",
        "",
        "## Concept Counts",
        "",
    ]
    for key in sorted(counts):
        lines.append(f"- {key}: {counts[key]}")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"repair: {REPAIR.relative_to(ROOT)} ({len(repair)} examples)")
    print(f"review: {REVIEW.relative_to(ROOT)} ({len(review)} examples)")
    print(f"tests: {TESTS.relative_to(ROOT)} ({len(TEST_ITEMS)} tests)")


if __name__ == "__main__":
    main()
