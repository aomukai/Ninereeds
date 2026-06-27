#!/usr/bin/env python3
"""Greedy concept-grounding eval for BDH checkpoints.

This is intentionally stricter than the general fluency eval. A response only
passes when it mentions expected concept evidence and avoids known contaminations.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from inference import BDHInference  # noqa: E402


DEFAULT_TESTS: list[dict[str, Any]] = [
    {
        "id": "dog_appearance_exact",
        "concept_id": "dog",
        "category": "animals",
        "source_corpus": "training_data/redesign/words/animals/dog_appearance.md",
        "prompt": "[user]what does a dog look like?\n[Ninereeds]",
        "required_any": [["four legs", "legs"], ["fur", "hair"], ["tail"], ["snout", "ears", "nose"]],
        "forbidden_any": ["straight", "wood", "plant", "place", "person", "machine"],
    },
    {
        "id": "dog_classification_exact",
        "concept_id": "dog",
        "category": "animals",
        "source_corpus": "training_data/redesign/words/animals/dog_classification.md",
        "prompt": "[user]what kind of thing is a dog?\n[Ninereeds]",
        "required_any": [["animal"], ["mammal", "pet"]],
        "forbidden_any": ["person", "place", "machine", "not a physical object", "straight"],
    },
    {
        "id": "dog_definition_exact",
        "concept_id": "dog",
        "category": "animals",
        "source_corpus": "training_data/redesign/words/animals/dog_what_is.md",
        "prompt": "[user]what is a dog?\n[Ninereeds]",
        "required_any": [["animal"], ["four legs", "legs"], ["fur", "barks", "pet", "people"]],
        "forbidden_any": ["person who", "place", "straight", "wood", "machine"],
    },
    {
        "id": "dog_boolean_chat",
        "concept_id": "dog",
        "category": "animals",
        "source_corpus": "training_data/redesign/words/animals/dog_classification.md",
        "prompt": "[user]Is a dog an animal?\n[Ninereeds]",
        "required_any": [["yes", "animal"]],
        "forbidden_any": ["i don't know", "quantity", "steady", "machine", "place"],
    },
    {
        "id": "airport_function_exact",
        "concept_id": "airport",
        "category": "places",
        "source_corpus": "training_data/redesign/words/places/airport_function.md",
        "prompt": "[user]what is an airport used for?\n[Ninereeds]",
        "required_any": [["airplane", "airplanes", "plane", "planes"], ["take off", "land", "landing"], ["travel", "cargo"]],
        "forbidden_any": ["store things", "plant", "person", "animal"],
    },
    {
        "id": "airplane_behavior_exact",
        "concept_id": "airplane",
        "category": "tools",
        "source_corpus": "training_data/redesign/words/tools/airplane_behavior.md",
        "prompt": "[user]what does an airplane do?\n[Ninereeds]",
        "required_any": [["moves", "move", "flies", "fly"], ["air"], ["take off", "land", "travels"]],
        "forbidden_any": ["story", "store", "tree", "person", "animal"],
    },
    {
        "id": "airplane_chat_how",
        "concept_id": "airplane",
        "category": "tools",
        "source_corpus": "training_data/redesign/words/tools/airplane_behavior.md",
        "prompt": "[user]How does an airplane work?\n[Ninereeds]",
        "required_any": [["air", "wings", "engine", "engines"], ["fly", "flies", "move", "moves", "lift"], ["take off", "land", "forward"]],
        "forbidden_any": ["story", "tree", "wire", "warp", "store"],
    },
]


@dataclass
class GroundingResult:
    id: str
    concept_id: str
    category: str
    prompt: str
    output: str
    score: float
    passed: bool
    required_hits: list[list[str]]
    required_misses: list[list[str]]
    forbidden_hits: list[str]
    source_corpus: str = ""
    trace: dict[str, Any] = field(default_factory=dict)


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def contains_phrase(text: str, phrase: str) -> bool:
    phrase = normalize(phrase)
    if " " in phrase:
        return phrase in text
    return bool(re.search(rf"\b{re.escape(phrase)}\b", text))


def load_tests(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return DEFAULT_TESTS
    tests: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                tests.append(json.loads(line))
    return tests


def load_trace(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["concept_id"]: item for item in data.get("concepts", [])}


def score_response(test: dict[str, Any], output: str, trace_by_concept: dict[str, dict[str, Any]]) -> GroundingResult:
    text = normalize(output)
    required_hits: list[list[str]] = []
    required_misses: list[list[str]] = []
    for group in test.get("required_any", []):
        hits = [phrase for phrase in group if contains_phrase(text, phrase)]
        if hits:
            required_hits.append(hits)
        else:
            required_misses.append(list(group))

    forbidden_hits = [
        phrase
        for phrase in test.get("forbidden_any", [])
        if contains_phrase(text, phrase)
    ]

    required_total = len(test.get("required_any", []))
    required_score = len(required_hits) / max(required_total, 1)
    forbidden_penalty = min(len(forbidden_hits) * 0.25, 1.0)
    score = max(0.0, required_score - forbidden_penalty)
    passed = required_score >= 0.67 and not forbidden_hits

    concept_id = test["concept_id"]
    trace_item = trace_by_concept.get(concept_id)
    trace = {}
    if trace_item:
        trace = {
            "avg_fire_rate": trace_item.get("avg_fire_rate"),
            "active_dims": trace_item.get("active_dims"),
            "probe_count": trace_item.get("probe_count"),
            "categories": trace_item.get("categories"),
            "source_corpus": trace_item.get("source_corpus"),
        }

    return GroundingResult(
        id=test["id"],
        concept_id=concept_id,
        category=test.get("category", ""),
        source_corpus=test.get("source_corpus", ""),
        prompt=test["prompt"],
        output=output,
        score=round(score, 3),
        passed=passed,
        required_hits=required_hits,
        required_misses=required_misses,
        forbidden_hits=forbidden_hits,
        trace=trace,
    )


def write_report(path: Path, checkpoint: str, config: dict[str, Any], results: list[GroundingResult]) -> None:
    passed = sum(1 for item in results if item.passed)
    avg_score = sum(item.score for item in results) / max(len(results), 1)
    lines = [
        "# Grounding Eval",
        "",
        f"- checkpoint: `{checkpoint}`",
        f"- config: `{json.dumps(config, sort_keys=True)}`",
        f"- pass_rate: `{passed}/{len(results)}`",
        f"- avg_score: `{avg_score:.3f}`",
        "",
        "## Results",
        "",
    ]
    for item in results:
        status = "PASS" if item.passed else "FAIL"
        trace_bits = ""
        if item.trace:
            trace_bits = f", fire={item.trace.get('avg_fire_rate'):.6f}, active_dims={item.trace.get('active_dims')}"
        lines.extend(
            [
                f"### {item.id} - {status}",
                "",
                f"- concept: `{item.concept_id}` / `{item.category}`{trace_bits}",
                f"- source: `{item.source_corpus}`",
                f"- score: `{item.score:.3f}`",
                f"- required_hits: `{item.required_hits}`",
                f"- required_misses: `{item.required_misses}`",
                f"- forbidden_hits: `{item.forbidden_hits}`",
                "",
                "Prompt:",
                "",
                "```text",
                item.prompt,
                "```",
                "",
                "Output:",
                "",
                "```text",
                item.output,
                "```",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run strict concept-grounding generation eval.")
    parser.add_argument("--checkpoint", required=True, help="Checkpoint to evaluate.")
    parser.add_argument("--tests", type=Path, help="Optional JSONL test suite.")
    parser.add_argument("--trace", type=Path, help="Optional brain trace JSON to enrich results.")
    parser.add_argument("--name", default="", help="Run name. Defaults to checkpoint stem plus timestamp.")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "training" / "logs" / "grounding_eval")
    parser.add_argument("--max-new-tokens", type=int, default=120)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--top-k", type=int, default=1)
    args = parser.parse_args()

    tests = load_tests(args.tests)
    trace_by_concept = load_trace(args.trace)
    run_name = args.name or f"{Path(args.checkpoint).stem}_{utc_timestamp()}"
    run_dir = args.out_dir
    run_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "max_new_tokens": args.max_new_tokens,
        "temperature": args.temperature,
        "top_k": args.top_k,
    }
    model = BDHInference(
        ROOT / args.checkpoint,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        top_k=args.top_k,
    )

    results: list[GroundingResult] = []
    for test in tests:
        output = model.generate_text(test["prompt"])
        for stop in ("\n[user]", "\n[Ninereeds]", "\n[User]"):
            if stop in output:
                output = output[: output.index(stop)].strip()
        output = output.replace("�", "").replace("◆", "").replace("￼", "").strip()
        results.append(score_response(test, output, trace_by_concept))

    payload = {
        "checkpoint": args.checkpoint,
        "config": config,
        "n_tests": len(results),
        "passed": sum(1 for item in results if item.passed),
        "avg_score": round(sum(item.score for item in results) / max(len(results), 1), 3),
        "results": [item.__dict__ for item in results],
    }
    json_path = run_dir / f"{run_name}.json"
    report_path = run_dir / f"{run_name}.md"
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_report(report_path, args.checkpoint, config, results)

    print(f"Grounding eval: {payload['passed']}/{payload['n_tests']} passed, avg_score={payload['avg_score']:.3f}")
    print(f"JSON: {json_path}")
    print(f"Report: {report_path}")
    for item in results:
        status = "PASS" if item.passed else "FAIL"
        print(f"{status} {item.id}: score={item.score:.3f} forbidden={item.forbidden_hits} missing={item.required_misses}")


if __name__ == "__main__":
    main()
