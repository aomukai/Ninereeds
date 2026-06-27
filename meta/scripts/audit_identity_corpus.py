#!/usr/bin/env python3
"""Audit Ninereeds identity corpus files for hard failures and style drift."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = ROOT / "training_data" / "kernel_identity"

TURN_RE = re.compile(r"^\[user\](.*?)\n\[Ninereeds\](.*?)(?=\n\[user\]|\Z)", re.DOTALL | re.MULTILINE)
BAD_PHRASES = [
    "i am chatgpt",
    "i'm chatgpt",
    "i am claude",
    "i'm claude",
    "i am deepseek",
    "i'm deepseek",
    "i am a human",
    "i'm a human",
    "i am human",
    "i am a person",
    "i'm a person",
    "i have a body",
    "i have eyes",
    "i can see you",
    "i can hear you",
    "i can browse",
    "i can search the internet",
    "as an ai language model",
    "developed by openai",
    "anthropic",
    "openai",
    "api",
    "policy",
    "i remember your name from before",
]
CONTRAST_TERMS = ("chatgpt", "claude", "deepseek", "human", "person", "robot", "animal", "internet")


def validate_turns(text: str) -> list[str]:
    issues: list[str] = []
    user_count = len(re.findall(r"^\[user\]", text, re.MULTILINE))
    bot_count = len(re.findall(r"^\[Ninereeds\]", text, re.MULTILINE))
    if user_count == 0:
        issues.append("no [user] tags")
    if user_count != bot_count:
        issues.append(f"mismatched turns: {user_count} user vs {bot_count} Ninereeds")
    if "```" in text:
        issues.append("markdown fence present")
    return issues


def sentence_count(answer: str) -> int:
    return len([part for part in re.split(r"[.!?]+", answer) if part.strip()])


def audit_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    issues = validate_turns(text)
    lower = text.lower()
    for phrase in BAD_PHRASES:
        if phrase in lower:
            issues.append(f"bad phrase: {phrase}")

    for prompt, answer in TURN_RE.findall(text.strip()):
        prompt_l = prompt.lower()
        answer_l = answer.lower()
        if any(term in prompt_l for term in CONTRAST_TERMS):
            if not answer_l.strip().startswith("no."):
                issues.append("contrast answer should start with 'No.'")
            if "ninereeds" not in answer_l:
                issues.append("contrast answer should identify Ninereeds")
            if len(answer.split()) > 18:
                issues.append(f"contrast answer too long: {len(answer.split())} words")
        if sentence_count(answer) > 3:
            issues.append(f"answer too long: {sentence_count(answer)} sentences")
        if len(answer.split()) > 35:
            issues.append(f"answer too verbose: {len(answer.split())} words")
        if "don't" in answer_l or "can't" in answer_l or "i'm" in answer_l:
            issues.append("contraction present")
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit generated identity corpus.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--max-issues", type=int, default=200)
    args = parser.parse_args()

    root = args.root if args.root.is_absolute() else ROOT / args.root
    files = sorted(root.rglob("*.md"))
    if not files:
        raise SystemExit(f"No identity files found under {root}")

    issue_count = 0
    for path in files:
        issues = audit_file(path)
        if not issues:
            continue
        for issue in issues:
            issue_count += 1
            if issue_count <= args.max_issues:
                print(f"{path.relative_to(ROOT)}: {issue}")

    if issue_count:
        raise SystemExit(f"Identity audit failed: {issue_count} issue(s)")
    print(f"OK: {len(files)} identity files")


if __name__ == "__main__":
    main()
