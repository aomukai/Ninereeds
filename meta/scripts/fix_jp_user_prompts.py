#!/usr/bin/env python3
"""
Fix English-in-[user]-line bugs in JP triplet story files.

For each file: reads the broken JP file + its EN counterpart, asks DeepSeek
to rewrite the [user] line into natural Japanese. Body is preserved unless
there are obvious structural artifacts (merged lines, EN editorial notes),
in which case DeepSeek cleans those up using the EN file as reference.

Queue:    tmp/jp_user_fix_queue.txt  (absolute paths, one per line)
Progress: tmp/jp_user_fix_done.txt   (completed absolute paths)

Usage:
  python3 meta/scripts/fix_jp_user_prompts.py [--batch 30] [--workers 5] [--dry-run]
"""

import argparse
import concurrent.futures
import json
import os
import pathlib
import re
import sys
import threading

from openai import OpenAI

BASE_URL = "https://openrouter.ai/api/v1"
MODEL    = "deepseek/deepseek-v4-flash"

QUEUE_FILE = pathlib.Path("tmp/jp_user_fix_queue.txt")
DONE_FILE  = pathlib.Path("tmp/jp_user_fix_done.txt")

SYSTEM_MSG = (
    "You are a corpus repair tool. Output ONLY the corrected file contents. "
    "No markdown fences, no commentary, no explanations."
)

PROMPT = """\
This is a Japanese story file from a language training corpus. Fix it according \
to the rules below.

## Problem
The [user] line contains English text or a mix of English and Japanese. \
Rewrite it into natural spoken Japanese.

## Rules
- Rewrite ONLY the [user] line. Do not retranslate or rewrite the [Ninereeds] story.
- The [user] line must contain no English letters after the [user] tag.
- Choose the most natural Japanese phrasing for the topic.
  Use varied forms, e.g.: 「〇〇の話をして。」「〇〇の話を聞かせて。」
  「〇〇について話して？」「〇〇についての話を聞かせてくれる？」
- For abstract or loan-word concepts, pick whatever sounds most natural — \
native Japanese (偶然、逆説、宇宙), katakana (チャンス、パラドックス、ユニバース), \
or a mix — based on the story context.
- If the [Ninereeds] body has obvious structural artifacts — lines merged without \
a newline, or English editorial notes like "— wait fix:" — clean those up too, \
using the EN reference to stay faithful to the story. Do not otherwise alter the body.
- The output must be exactly two non-empty lines: one [user] line, one [Ninereeds] line.

## EN reference (same story — use for topic and context only):
{en_content}

## Broken JP file to fix:
{jp_content}
"""

_print_lock = threading.Lock()


def _log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def load_api_key() -> str:
    for var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        if k := os.environ.get(var):
            return k
    auth = pathlib.Path.home() / ".local/share/opencode/auth.json"
    try:
        data = json.loads(auth.read_text())
        v = data.get("openrouter", "")
        return v.get("key", "") if isinstance(v, dict) else v
    except Exception:
        return ""


def en_path(jp: pathlib.Path) -> pathlib.Path:
    return jp.with_name(jp.name.replace("_JP.md", "_EN.md"))


def verify(content: str) -> tuple[bool, str]:
    lines = [l for l in content.splitlines() if l.strip()]
    user_lines  = [l for l in lines if l.startswith("[user]")]
    nine_lines  = [l for l in lines if l.startswith("[Ninereeds]")]
    if not user_lines:
        return False, "missing [user] line"
    if not nine_lines:
        return False, "missing [Ninereeds] line"
    body = user_lines[0][len("[user]"):]
    if re.search(r"[a-zA-Z]", body):
        return False, f"English still present: {body[:60]}"
    return True, "OK"


def fix_one(jp: pathlib.Path, client: OpenAI, dry_run: bool) -> bool:
    try:
        jp_content = jp.read_text()
        en = en_path(jp)
        en_content = en.read_text() if en.exists() else "(EN file not found)"

        if dry_run:
            _log(f"  [DRY RUN] {jp.name}")
            return True

        prompt = PROMPT.format(en_content=en_content.strip(),
                               jp_content=jp_content.strip())

        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_MSG},
                {"role": "user",   "content": prompt},
            ],
            max_tokens=4096,
        )

        result = (resp.choices[0].message.content or "").strip()

        # Strip accidental markdown fences
        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        ok, reason = verify(result)
        if not ok:
            _log(f"  FAIL {jp.name}: {reason}")
            return False

        jp.write_text(result + "\n")
        tok_in  = resp.usage.prompt_tokens       if resp.usage else "?"
        tok_out = resp.usage.completion_tokens   if resp.usage else "?"
        _log(f"  OK   {jp.name} ({tok_in}→{tok_out})")
        return True

    except Exception as e:
        _log(f"  ERROR {jp.name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Fix English in JP [user] lines")
    parser.add_argument("--batch",   type=int, default=30)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    api_key = load_api_key()
    if not api_key and not args.dry_run:
        print("ERROR: No OpenRouter API key found.", file=sys.stderr)
        print("Set OPENROUTER_API_KEY env var.", file=sys.stderr)
        sys.exit(1)

    if not QUEUE_FILE.exists():
        print(f"ERROR: {QUEUE_FILE} not found.", file=sys.stderr)
        sys.exit(1)

    done: set[str] = set()
    if DONE_FILE.exists():
        done = set(DONE_FILE.read_text().splitlines())

    queue = [
        pathlib.Path(l.strip())
        for l in QUEUE_FILE.read_text().splitlines()
        if l.strip() and l.strip() not in done
    ]

    if not queue:
        print("All files already done.")
        return

    batch  = queue[: args.batch]
    client = OpenAI(api_key=api_key or "dummy", base_url=BASE_URL)

    print(f"Processing {len(batch)} of {len(queue)} remaining  ({args.workers} workers)...")
    print()

    results: list[tuple[pathlib.Path, bool]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(fix_one, p, client, args.dry_run): p for p in batch}
        for future in concurrent.futures.as_completed(futures):
            p       = futures[future]
            success = future.result()
            results.append((p, success))
            if success and not args.dry_run:
                with _print_lock:
                    with open(DONE_FILE, "a") as f:
                        f.write(str(p) + "\n")

    ok   = sum(1 for _, s in results if s)
    fail = sum(1 for _, s in results if not s)
    remaining = len(queue) - ok

    print()
    print("RECEIPT")
    print("-------")
    print(f"Processed: {len(batch)}  OK: {ok}  Failed: {fail}")
    print(f"Remaining: {remaining}")
    print(f"Status: {'DONE' if remaining == 0 else 'IN_PROGRESS'}")


if __name__ == "__main__":
    main()
