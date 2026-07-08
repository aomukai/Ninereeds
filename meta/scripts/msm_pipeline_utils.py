#!/usr/bin/env python3
"""Small deterministic helpers for the MSM pipeline.

This module intentionally avoids embeddings and model calls. It provides the current
fixed executor-selection stub and a cheap structural fingerprint for script de-duplication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


WORD_RE = re.compile(r"[a-z0-9']+")
ARTICLES = {"a", "an", "the"}


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
    return " ".join(WORD_RE.findall(text.lower()))


def short_phrase(text: str) -> str:
    words = WORD_RE.findall(text.lower())
    return " ".join(words[:4]).strip()


def content_tokens(text: str) -> list[str]:
    return [token for token in WORD_RE.findall(text.lower()) if token not in ARTICLES]


def infer_question_type(prompt: str) -> str:
    text = normalize_text(prompt)
    if text.startswith(("is ", "are ", "do ", "does ", "can ", "has ", "have ")):
        if " or " in text:
            return "or_question"
        return "yes_no"
    if text.startswith(("what ", "who ", "where ", "when ", "why ", "how ")):
        return text.split(" ", 1)[0] + "_question"
    if " or " in text:
        return "or_question"
    return "statement_or_prompt"


def extract_contrast_pairs(*texts: str) -> list[list[str]]:
    pairs: set[tuple[str, str]] = set()
    for raw_text in texts:
        tokens = content_tokens(raw_text)
        for index, token in enumerate(tokens):
            if token not in {"is", "are"}:
                continue
            if index + 2 < len(tokens) and tokens[index + 1] == "not":
                left = tokens[index - 1] if index > 0 else ""
                right = tokens[index + 2]
            elif index == 0 and index + 2 < len(tokens):
                left = tokens[index + 1]
                right = tokens[index + 2]
            elif index > 0 and index + 1 < len(tokens):
                left = tokens[index - 1]
                right = tokens[index + 1]
            else:
                continue
            if left and right and left != right:
                pairs.add((left, right))
    return [list(pair) for pair in sorted(pairs)]


def compute_script_fingerprint(script: dict[str, Any]) -> dict[str, Any]:
    items = script.get("items", [])
    if not isinstance(items, list):
        raise ValueError("script.items must be a list")

    question_type_sequence: list[str] = []
    prompt_tokens: list[list[str]] = []
    contrast_pairs: list[list[str]] = []

    for item in items:
        if not isinstance(item, dict):
            raise ValueError("script.items entries must be objects")
        prompt = str(item.get("user_prompt", ""))
        correction = item.get("teacher_correction")
        correction_text = "" if correction is None else str(correction)
        question_type_sequence.append(infer_question_type(prompt))
        prompt_tokens.append(WORD_RE.findall(normalize_text(prompt)))
        contrast_pairs.extend(extract_contrast_pairs(prompt, correction_text))

    unique_pairs = [list(pair) for pair in sorted({tuple(pair) for pair in contrast_pairs})]
    stages = [str(item.get("stage", "")) for item in items if isinstance(item, dict)]
    targets = sorted(
        {
            str(target)
            for item in items
            if isinstance(item, dict)
            for target in item.get("target_failure_modes", [])
        }
    )
    structural_payload = {
        "card_id": script.get("card_id"),
        "session_mode": script.get("session_mode"),
        "stages": stages,
        "question_type_sequence": question_type_sequence,
        "contrast_pairs": unique_pairs,
        "target_failure_modes": targets,
    }
    prompt_payload = {
        "prompts": [normalize_text(str(item.get("user_prompt", ""))) for item in items if isinstance(item, dict)],
        "corrections": [
            normalize_text(str(item.get("teacher_correction", "")))
            for item in items
            if isinstance(item, dict)
        ],
    }
    return {
        "algorithm": "msm_script_fingerprint_v1",
        "structural_hash": stable_hash(structural_payload),
        "prompt_hash": stable_hash(prompt_payload),
        "question_type_sequence": question_type_sequence,
        "contrast_pairs": unique_pairs,
    }


def prompt_jaccard(script_a: dict[str, Any], script_b: dict[str, Any]) -> float:
    def tokens(script: dict[str, Any]) -> set[str]:
        values: set[str] = set()
        for item in script.get("items", []):
            if isinstance(item, dict):
                values.update(WORD_RE.findall(normalize_text(str(item.get("user_prompt", "")))))
                values.update(WORD_RE.findall(normalize_text(str(item.get("teacher_correction", "")))))
        return values

    a = tokens(script_a)
    b = tokens(script_b)
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def select_executor(orchestrator_config: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, str]:
    selection = orchestrator_config.get("executor_selection", {})
    mode = selection.get("selection_mode", "fixed")
    if mode != "fixed":
        raise ValueError(f"unsupported executor selection_mode: {mode!r}")
    executor = selection.get("default_executor")
    if not isinstance(executor, str) or not executor:
        raise ValueError("executor_selection.default_executor must be a non-empty string")
    return {"executor_id": executor, "selection_method": "fixed"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    fp = sub.add_parser("fingerprint", help="compute a script fingerprint")
    fp.add_argument("script", type=Path)
    args = parser.parse_args(argv)

    if args.cmd == "fingerprint":
        script = load_json(args.script)
        print(json.dumps(compute_script_fingerprint(script), indent=2, sort_keys=True))
        return 0
    raise AssertionError(args.cmd)


if __name__ == "__main__":
    sys.exit(main())
