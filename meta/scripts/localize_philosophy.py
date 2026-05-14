#!/usr/bin/env python3
"""
localize_philosophy.py - Expand EN-only philosophy dialogues into multilingual format.

Rewrites training_data/philosophy/dialogues_cat*.md in place.

Each tag is expanded to 4 language variants grouped together:
  [STATEMENT]  →  [STATEMENT_EN]  [STATEMENT_DE]  [STATEMENT_JA]  [STATEMENT_ZH]
  [USER]       →  [USER_EN]       [USER_DE]       [USER_JA]       [USER_ZH]
  [NINEREEDS]  →  [NINEREEDS_EN]  [NINEREEDS_DE]  [NINEREEDS_JA]  [NINEREEDS_ZH]

Usage:
  python3 meta/scripts/localize_philosophy.py [--workers 4] [--dry-run]
  python3 meta/scripts/localize_philosophy.py report
"""

import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent.parent
PHIL_DIR = ROOT / "training_data" / "philosophy"
MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_WORKERS = 4

PROMPT_TEMPLATE = """You are expanding an English philosophy dialogue into a multilingual format.

TASK: Replace each source tag with 4 language variants, grouped together in EN/DE/JA/ZH order.

  [STATEMENT] becomes:
    [STATEMENT_EN]
    (source text, copied verbatim)

    [STATEMENT_DE]
    (German version)

    [STATEMENT_JA]
    (Japanese version)

    [STATEMENT_ZH]
    (Traditional Chinese version)

  Apply the same pattern to [USER] → [USER_EN/DE/JA/ZH] and [NINEREEDS] → [NINEREEDS_EN/DE/JA/ZH].

REGISTERS:

EN — copy source text exactly. Do not alter, paraphrase, or summarize.

DE — precise philosophical prose, like a serious German essay or school text (not stiff academic, not casual):
  - STATEMENT/NINEREEDS: clear declarative sentences. Formal vocabulary, natural flow.
  - USER: natural conversational question. Du-form is fine.
  - Example Ninereeds tone: "Das Gewicht ist real. Die Härte ist real. Aber denk darüber nach, was den Stuhl zu einem Stuhl macht..."

JA — である体 for STATEMENT and NINEREEDS; natural conversational for USER:
  - STATEMENT/NINEREEDS: 〜とは〜である。〜しかし〜。 style. Light and readable — not stiff.
    Avoid: 〜のである、長い受け身構文、〜において
    Prefer: short declarative sentences, active voice
  - USER: natural, slightly casual. でも、〜じゃないですか？ or でも、〜ではないか？
  - Example STATEMENT tone: 重さは本物だ。硬さも本物だ。しかし、何が椅子を椅子たらしめているか考えてみよう。

ZH — Traditional Chinese (繁體中文), Standard Written style:
  - STATEMENT/NINEREEDS: no spoken particles (啊、嘛、吧、呢). Clear, precise.
  - USER: natural written question. No particles.
  - Example tone: 重量是真實的。硬度也是真實的。但想想看，是什麼讓椅子成為椅子...

FORMATTING:
- One blank line between each language block within a section.
- One blank line between sections (e.g., between [STATEMENT_ZH] block and [USER_EN] block).
- Output ONLY the expanded file content — no preamble, no explanation, no fences.

--- SOURCE ---
{source}
--- END SOURCE ---"""


def get_api_key():
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        auth = Path.home() / ".local/share/opencode/auth.json"
        if auth.exists():
            data = json.loads(auth.read_text())
            key = data.get("openrouter", {}).get("key")
    if not key:
        raise RuntimeError("No API key found. Set OPENROUTER_API_KEY.")
    return key


def is_done(content: str) -> bool:
    return "[STATEMENT_EN]" in content


def validate(source: str, output: str) -> list[str]:
    errors = []
    for tag in ("STATEMENT", "USER", "NINEREEDS"):
        src_count = source.count(f"[{tag}]")
        for lang in ("EN", "DE", "JA", "ZH"):
            out_count = output.count(f"[{tag}_{lang}]")
            if out_count != src_count:
                errors.append(f"[{tag}_{lang}] count: expected {src_count}, got {out_count}")
    return errors


def process_file(path: Path, client: OpenAI, dry_run: bool) -> str:
    source = path.read_text(encoding="utf-8")
    if is_done(source):
        return f"  SKIP {path.name} — already multilingual"
    if dry_run:
        return f"  WOULD EXPAND {path.name}  ({len(source)} chars)"

    extra = ""
    for attempt in range(1, 3):
        prompt = PROMPT_TEMPLATE.format(source=source.strip())
        if extra:
            prompt += f"\n\nPREVIOUS ATTEMPT ERRORS — fix all:\n{extra}"
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                max_tokens=32768,
                messages=[{"role": "user", "content": prompt}],
            )
            output = resp.choices[0].message.content.strip()
        except Exception as e:
            if attempt == 2:
                return f"  ERROR {path.name}: {e}"
            continue

        errors = validate(source, output)
        if errors:
            if attempt == 1:
                print(f"  VALIDATE FAIL (attempt 1) {path.name}:")
                for e in errors:
                    print(f"    {e}")
                extra = "\n".join(f"- {e}" for e in errors)
                continue
            return f"  FAIL {path.name}: {'; '.join(errors)}"

        path.write_text(output + "\n", encoding="utf-8")
        return f"  OK {path.name}  ({len(source)}→{len(output)})"

    return f"  FAIL {path.name}: unknown"


def cmd_report():
    files = sorted(PHIL_DIR.glob("dialogues_cat*.md"))
    done = sum(1 for f in files if is_done(f.read_text(encoding="utf-8")))
    print(f"Philosophy files: {len(files)} total, {done} expanded, {len(files)-done} remaining")


def cmd_gen(args):
    dry_run = "--dry-run" in args
    workers = DEFAULT_WORKERS
    for i, a in enumerate(args):
        if a == "--workers" and i + 1 < len(args):
            workers = int(args[i + 1])
        elif a.startswith("--workers="):
            workers = int(a.split("=", 1)[1])

    if dry_run:
        print("(dry run — no files will be written)\n")

    api_key = get_api_key()
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    files = sorted(PHIL_DIR.glob("dialogues_cat*.md"))
    print(f"Philosophy files: {len(files)} | Workers: {workers}\n")

    ok = fail = skip = 0
    lock = threading.Lock()

    def run(path):
        nonlocal ok, fail, skip
        result = process_file(path, client, dry_run)
        with lock:
            print(result)
            if "OK" in result or "WOULD" in result:
                ok += 1
            elif "SKIP" in result:
                skip += 1
            else:
                fail += 1

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(as_completed([ex.submit(run, f) for f in files]))

    print(f"\nDone: {ok} expanded, {skip} skipped, {fail} failed.")


def main():
    args = sys.argv[1:]
    if not args or args[0] == "report":
        cmd_report()
    elif args[0] == "gen":
        cmd_gen(args[1:])
    else:
        print("Usage: localize_philosophy.py [gen|report] [options]")
        sys.exit(1)


if __name__ == "__main__":
    main()
