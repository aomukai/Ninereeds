#!/usr/bin/env python3
"""
repair_incomplete_phases.py

Repairs phase files that have fewer than 4 [user]/[Ninereeds] pairs.
Sends each file to DeepSeek via OpenRouter and writes the result back.

Queue:    training_data/phases/repair_incomplete.txt  (one absolute path per line)
Progress: training_data/phases/repair_incomplete_done.txt

Usage:
  python3 meta/scripts/repair_incomplete_phases.py [--workers 4] [--batch 20] [--dry-run]

Auth: set OPENROUTER_API_KEY env var (or OPENAI_API_KEY as fallback).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai package not installed. Run: pip install openai")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent.parent
QUEUE_FILE = ROOT / "training_data/phases/repair_incomplete.txt"
DONE_FILE = ROOT / "training_data/phases/repair_incomplete_done.txt"

MODEL = "deepseek/deepseek-chat"
MAX_TOKENS = 2048
TEMPERATURE = 0.3

SYSTEM_PROMPT = """\
You are a training data repair specialist for a language model.
You write structured dialogue files in a strict format.

FORMAT RULES (follow exactly):
- Exactly 4 [user]/[Ninereeds] block pairs per file, separated by a blank line
- [user] tag on the same line as the question, no space after the tag
- [Ninereeds] tag on the same line as the first response line, no space after the tag
- Each [Ninereeds] response: exactly 5 body lines + 1 summary line
- One sentence per line, one period per line
- No pronouns (it, its, they, them, he, she, etc.)
- No negation in body lines (no "not", "isn't", "doesn't", etc.)
- The subject of every line is the word/concept being taught or a part of it
- Summary line: combines two properties from the body lines

Example of correct format:
[user]What does frost look like?
[Ninereeds]Frost is a white layer.
Frost is thin.
Frost is cold.
Frost covers a surface.
Frost forms at night.
Frost is a thin white layer that covers surfaces.

[user]Where can you find frost?
[Ninereeds]Frost appears on glass.
Frost appears on leaves.
Frost appears on grass.
Frost appears on metal.
Frost appears on the ground.
Frost appears on glass and on leaves.
""".strip()


def make_repair_prompt(word: str, existing: str) -> str:
    """Build a prompt asking DeepSeek to write the full 4-pair file for this word."""
    return (
        f"Rewrite this training file for the word '{word}' following the format rules exactly.\n"
        f"Generate all 4 question-answer pairs. The questions should be:\n"
        f"1. What does {word} look like? (or: What does {word} mean? for abstract words)\n"
        f"2. Where can you find {word}? (or: Where does {word} appear?)\n"
        f"3. What does {word} do?\n"
        f"4. What does {word} give? (or: What is {word} for?)\n\n"
        f"Existing content (may be incomplete or malformed — use only as context for the word):\n"
        f"---\n{existing}\n---\n\n"
        f"Output ONLY the repaired file content, no explanation, no markdown fences."
    )


def get_api_client() -> OpenAI:
    key = (
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )
    if not key:
        raise RuntimeError(
            "No API key found. Set OPENROUTER_API_KEY env var."
        )
    return OpenAI(
        api_key=key,
        base_url="https://openrouter.ai/api/v1",
    )


def validate_repair(text: str) -> list[str]:
    """Return list of issues; empty list = OK."""
    user_count = len(re.findall(r"^\[user\]", text, re.MULTILINE))
    nr_count = len(re.findall(r"^\[Ninereeds\]", text, re.MULTILINE))
    issues = []
    if user_count != 4:
        issues.append(f"[user] count {user_count}, expected 4")
    if nr_count != 4:
        issues.append(f"[Ninereeds] count {nr_count}, expected 4")
    if not issues:
        nr_with_content = len(re.findall(r"^\[Ninereeds\].+", text, re.MULTILINE))
        if nr_with_content != 4:
            issues.append(f"{4 - nr_with_content} [Ninereeds] opener(s) missing inline content")
    return issues


def repair_file(client: OpenAI, path: Path, dry_run: bool) -> tuple[str, str]:
    """Repair one file. Returns (path_str, 'ok'/'skip'/'error:...')."""
    word = path.stem
    existing = path.read_text(encoding="utf-8", errors="replace")

    if dry_run:
        return str(path), "dry-run"

    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": make_repair_prompt(word, existing)},
                ],
            )
            result = response.choices[0].message.content.strip()

            # Strip markdown fences if present
            result = re.sub(r"^```[a-z]*\n?", "", result)
            result = re.sub(r"\n?```$", "", result)
            result = result.strip() + "\n"

            issues = validate_repair(result)
            if not issues:
                path.write_text(result, encoding="utf-8")
                return str(path), "ok"
            elif attempt == 0:
                continue  # retry once
            else:
                return str(path), f"error:validation {issues}"
        except Exception as e:
            if attempt == 0:
                time.sleep(2)
                continue
            return str(path), f"error:{e}"

    return str(path), "error:exhausted"


def load_queue(batch_size: int) -> list[Path]:
    if not QUEUE_FILE.exists():
        return []
    done = set()
    if DONE_FILE.exists():
        done = set(DONE_FILE.read_text().splitlines())

    paths = []
    for line in QUEUE_FILE.read_text().splitlines():
        line = line.strip()
        if line and line not in done:
            paths.append(Path(line))
            if len(paths) >= batch_size:
                break
    return paths


def mark_done(path: Path) -> None:
    with DONE_FILE.open("a", encoding="utf-8") as f:
        f.write(str(path) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair incomplete phase files")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--batch", type=int, default=20,
                        help="Files to process per run (default 20)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be repaired without writing")
    args = parser.parse_args()

    paths = load_queue(args.batch)
    if not paths:
        print("Queue empty or all files already done.")
        return

    done_count = len(DONE_FILE.read_text().splitlines()) if DONE_FILE.exists() else 0
    total_count = sum(1 for l in QUEUE_FILE.read_text().splitlines() if l.strip())
    print(f"Repairing {len(paths)} files  ({done_count}/{total_count} done so far)")

    client = get_api_client() if not args.dry_run else None
    ok = skipped = errors = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(repair_file, client, p, args.dry_run): p
            for p in paths
        }
        for future in as_completed(futures):
            path_str, status = future.result()
            name = Path(path_str).name
            if status == "ok":
                mark_done(Path(path_str))
                ok += 1
                print(f"  OK       {name}")
            elif status == "dry-run":
                skipped += 1
                print(f"  dry-run  {name}")
            else:
                errors += 1
                print(f"  FAIL     {name}  {status}")

    print(f"\n  ok={ok}  skipped={skipped}  errors={errors}")


if __name__ == "__main__":
    main()
