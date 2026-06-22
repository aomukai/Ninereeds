#!/usr/bin/env python3
"""
Repair education dialogue files with mismatched [user]/[Ninereeds] counts.

Reads a list of broken files, sends each to DeepSeek for repair,
validates the result, and writes it back. Safe to run while training
is using other corpus files.

Usage:
  python3 meta/scripts/repair_education_mismatches.py [--workers 4] [--dry-run]

Queue file: tmp/edu_repair_queue.txt  (one relative path per line)
Done file:  tmp/edu_repair_done.txt
"""

import argparse
import concurrent.futures
import os
import pathlib
import re
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parents[2]
QUEUE_FILE = ROOT / "tmp" / "edu_repair_queue.txt"
DONE_FILE  = ROOT / "tmp" / "edu_repair_done.txt"

FORMAT_SPEC = """
## Education dialogue format

These are Socratic dialogues where Ninereeds (a small AI) asks questions and the user (a student/teacher) answers.

Rules:
- [Ninereeds] turns always contain a question (end with ?)
- [user] turns contain the answer or explanation
- Tags are on the SAME LINE as content: `[Ninereeds]Why does X happen?` and `[user]X happens because...`
- [Ninereeds] and [user] turns alternate (either may go first)
- Counts must match: every [user] turn has exactly one [Ninereeds] partner
- No blank lines within a turn; one blank line between turns
- Preserve the language of the file exactly (EN, DE, JP, or ZH)
- Do not change existing content — only add the missing turn(s) to fix the mismatch
"""

REPAIR_PROMPT = """{format_spec}

## File to repair

Path: {path}

Current content (has mismatched [user]/[Ninereeds] counts — {issue}):

```
{content}
```

## Task

Fix the mismatch by adding the missing turn(s). Do not change any existing content.
Output ONLY the complete repaired file content with no markdown fences, no explanation.
"""

_done_lock = threading.Lock()


def get_api_key() -> str:
    for var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        if os.environ.get(var):
            return os.environ[var]
    auth = pathlib.Path.home() / ".local/share/opencode/auth.json"
    if auth.exists():
        import json
        data = json.loads(auth.read_text())
        key = data.get("openrouter", {}).get("key") or data.get(".openrouter", {}).get("key")
        if key:
            return key
    sys.exit("No API key found. Set OPENROUTER_API_KEY.")


def count_tags(text: str) -> tuple[int, int]:
    user = len(re.findall(r"^\[user\]", text, re.MULTILINE))
    nr   = len(re.findall(r"^\[Ninereeds\]", text, re.MULTILINE))
    return user, nr


def fix_newline_tags(text: str) -> str:
    """Merge bare [Tag] lines with the following content line."""
    lines = text.split("\n")
    result: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped in ("[Ninereeds]", "[user]"):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                result.append(stripped + lines[j].strip())
                i = j + 1
                continue
        result.append(lines[i])
        i += 1
    return "\n".join(result)


def validate(text: str) -> list[str]:
    issues = []
    user, nr = count_tags(text)
    if user == 0:
        issues.append("no [user] tags")
    elif user != nr:
        issues.append(f"still mismatched: {user} [user] vs {nr} [Ninereeds]")
    empty_nr = len(re.findall(r"^\[Ninereeds\]$", text, re.MULTILINE))
    if empty_nr:
        issues.append(f"{empty_nr} [Ninereeds] opener(s) with no content")
    return issues


def repair_file(rel_path: str, client, dry_run: bool) -> str:
    path = ROOT / rel_path
    if not path.exists():
        return f"SKIP (not found): {rel_path}"

    original = path.read_text(encoding="utf-8")
    user, nr = count_tags(original)
    issue = f"{user} [user] vs {nr} [Ninereeds]"

    prompt = REPAIR_PROMPT.format(
        format_spec=FORMAT_SPEC,
        path=rel_path,
        issue=issue,
        content=original,
    )

    try:
        resp = client.chat.completions.create(
            model="deepseek/deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.2,
        )
        repaired = resp.choices[0].message.content.strip()
    except Exception as e:
        return f"FAIL (API error): {rel_path}: {e}"

    # strip accidental markdown fences
    if repaired.startswith("```"):
        lines = repaired.split("\n")
        repaired = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    repaired = fix_newline_tags(repaired)
    remaining_issues = validate(repaired)
    if remaining_issues:
        return f"FAIL (validation): {rel_path}: {'; '.join(remaining_issues)}"

    if not dry_run:
        path.write_text(repaired, encoding="utf-8")
        with _done_lock:
            with open(DONE_FILE, "a") as f:
                f.write(rel_path + "\n")

    return f"OK: {rel_path}"


def load_queue() -> list[str]:
    if not QUEUE_FILE.exists():
        return []
    done = set()
    if DONE_FILE.exists():
        done = set(DONE_FILE.read_text().splitlines())
    return [
        line.strip()
        for line in QUEUE_FILE.read_text().splitlines()
        if line.strip() and not line.startswith("#") and line.strip() not in done
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    queue = load_queue()
    if not queue:
        print("Queue empty or all done.")
        return

    print(f"Repairing {len(queue)} files  (workers={args.workers}, dry-run={args.dry_run})")

    from openai import OpenAI
    client = OpenAI(api_key=get_api_key(), base_url="https://openrouter.ai/api/v1")

    DONE_FILE.parent.mkdir(exist_ok=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(repair_file, p, client, args.dry_run): p for p in queue}
        for fut in concurrent.futures.as_completed(futures):
            print(fut.result())

    remaining = load_queue()
    print(f"\nDone. {len(queue) - len(remaining)} repaired, {len(remaining)} remaining.")


if __name__ == "__main__":
    main()
