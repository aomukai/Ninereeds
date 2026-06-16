#!/usr/bin/env python3
"""
audit_annotations.py — Sample _marked.md files and ask DeepSeek to review them.

Samples N files per tier (stratified), sends each to DeepSeek for review,
collects issues, writes report to training_data/audit.md.

Usage:
  python3 meta/scripts/audit_annotations.py [--per-tier 12] [--workers 6]
"""
from __future__ import annotations

import argparse
import os
import random
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent.parent

_env = ROOT / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if _line.strip() and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

STORIES_DIR = ROOT / "training_data" / "01_language" / "teaching_stories"
AUDIT_OUT   = ROOT / "training_data" / "audit.md"
MODEL       = "deepseek/deepseek-v4-flash"
MAX_TOKENS  = 4096
TEMPERATURE = 0.1

_print_lock = threading.Lock()

AUDIT_PROMPT = """\
You are auditing a teaching story annotation. The file contains a story in 4 languages \
(EN, DE, JP, ZH) with case-role bracket annotations applied to the [Ninereeds] answer blocks.

EXPECTED ANNOTATION SCHEME:
  (NOM) = subject performing the action — required in EVERY sentence
  *verb* = main content verb — required in EVERY sentence
  {ACC} = direct object (acted upon directly)
  [DAT] = indirect object or dative prepositional phrase
  <GEN> = genitive / possessive ("of X", "X's", の, 的)

RULES:
1. EVERY sentence in a [Ninereeds] block must have both (NOM) and *verb*.
2. [user] lines must NOT be annotated — left exactly as plain text.
3. Brackets must wrap the correct constituent — not split mid-phrase, not applied to adjectives alone.
4. {ACC}, [DAT], <GEN> only where the role is actually present — do not force-add.
5. The same semantic role should be bracketed consistently across all 4 languages.
6. No extra text, reasoning notes, or commentary outside the [user]/[Ninereeds] structure.

ANNOTATED FILE:
---
{content}
---

Respond in this exact format:

VERDICT: OK
(if no issues found)

OR:

VERDICT: ISSUES
ISSUE 1: [brief description — what's wrong and which language/sentence]
ISSUE 2: ...
(list all issues found, numbered, one per line)

Do NOT explain the annotation rules back. Do NOT quote large sections of the file. \
Be concise — one line per issue."""


def call_api(prompt: str, api_key: str) -> str:
    from openai import OpenAI
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    resp = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        messages=[{"role": "user", "content": prompt}],
    )
    content = resp.choices[0].message.content or ""
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    return content


def audit_file(path: Path, api_key: str) -> tuple[Path, str, str]:
    """Returns (path, verdict, raw_response)."""
    text = path.read_text("utf-8")
    prompt = AUDIT_PROMPT.replace("{content}", text)
    try:
        response = call_api(prompt, api_key)
    except Exception as e:
        return (path, "ERROR", str(e))

    if "VERDICT: OK" in response:
        return (path, "OK", response)
    elif "VERDICT: ISSUES" in response:
        return (path, "ISSUES", response)
    else:
        return (path, "UNKNOWN", response)


def sample_files(per_tier: int) -> list[Path]:
    """Stratified random sample across tiers."""
    files: list[Path] = []
    for tier_dir in sorted(STORIES_DIR.iterdir()):
        if not tier_dir.is_dir() or not tier_dir.name.startswith("tier_"):
            continue
        tier_files = sorted(tier_dir.rglob("*_marked.md"))
        if not tier_files:
            continue
        k = min(per_tier, len(tier_files))
        sample = random.sample(tier_files, k)
        files.extend(sorted(sample))
    return files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-tier", type=int, default=12,
                        help="Files to sample per tier (default 12 → ~48 total for 4 tiers)")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("ERROR: OPENROUTER_API_KEY not set")

    sample = sample_files(args.per_tier)
    print(f"Auditing {len(sample)} files ({args.per_tier} per tier) with {args.workers} workers...")

    results: list[tuple[Path, str, str]] = []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(audit_file, p, api_key): p for p in sample}
        done = 0
        for fut in as_completed(futures):
            path, verdict, response = fut.result()
            done += 1
            rel = path.relative_to(STORIES_DIR)
            with _print_lock:
                print(f"  [{done:3d}/{len(sample)}] {verdict:7s}  {rel}")
            results.append((path, verdict, response))

    # Sort results: ISSUES first, then OK, then errors
    order = {"ISSUES": 0, "ERROR": 1, "UNKNOWN": 2, "OK": 3}
    results.sort(key=lambda r: (order.get(r[1], 9), str(r[0])))

    ok_count     = sum(1 for _, v, _ in results if v == "OK")
    issue_count  = sum(1 for _, v, _ in results if v == "ISSUES")
    error_count  = sum(1 for _, v, _ in results if v not in ("OK", "ISSUES"))

    # Build report
    lines = [
        f"# Annotation Audit — {date.today().isoformat()}",
        "",
        f"Sample: {len(sample)} files ({args.per_tier} per tier, seed={args.seed})",
        f"Model: {MODEL}",
        "",
        f"| Verdict | Count |",
        f"|---------|-------|",
        f"| OK      | {ok_count} |",
        f"| ISSUES  | {issue_count} |",
        f"| ERROR   | {error_count} |",
        "",
        "---",
        "",
    ]

    if issue_count or error_count:
        lines.append("## Files with issues")
        lines.append("")
        for path, verdict, response in results:
            if verdict == "OK":
                continue
            rel = path.relative_to(ROOT)
            lines.append(f"### `{rel}`")
            lines.append("")
            # Extract just the issue lines
            issue_lines = [
                l for l in response.splitlines()
                if l.strip() and not l.startswith("VERDICT:")
            ]
            for il in issue_lines:
                lines.append(il)
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Clean files")
    lines.append("")
    for path, verdict, _ in results:
        if verdict == "OK":
            rel = path.relative_to(ROOT)
            lines.append(f"- `{rel}`")

    report = "\n".join(lines) + "\n"
    AUDIT_OUT.write_text(report, "utf-8")
    print(f"\nReport written to {AUDIT_OUT.relative_to(ROOT)}")
    print(f"Summary: {ok_count} OK, {issue_count} with issues, {error_count} errors")


if __name__ == "__main__":
    main()
