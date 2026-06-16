#!/usr/bin/env python3
"""
retrofit_bridge_persons.py — Replace named characters with generic NPs in bridge files.

Emma → the girl / das Mädchen / 女の子 / 那個女孩
Gran → the woman / die Frau / 女の人 / 那個女人
Taro → the man / der Mann / 男の人 / 那個男人

Uses DeepSeek via OpenRouter. API key read from .env (OPENROUTER_API_KEY).

Usage:
  python3 meta/scripts/retrofit_bridge_persons.py [--workers 4] [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

_env = ROOT / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if _line.strip() and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

BRIDGE_DIR = ROOT / "training_data" / "01_language" / "bridge"
DONE_FILE  = ROOT / "tmp" / "retrofit_bridge_done.txt"
MODEL      = "deepseek/deepseek-v4-flash"
MAX_TOKENS = 4096
TEMPERATURE = 0.3

NAMED_CHARS = ("Emma", "Gran", "Taro")

_print_lock = threading.Lock()

PROMPT_TEMPLATE = """\
Rewrite this grammar bridge training file. Replace the named character with the appropriate \
generic person NP. Keep the EXACT file format and every other word unchanged.

Character replacements:
  Emma → EN: "the girl"  | DE: "das Mädchen" | JP: "女の子" (with particle が inside brackets: 女の子が) | ZH: "那個女孩"
  Gran → EN: "the woman" | DE: "die Frau"     | JP: "女の人" (with particle が inside brackets: 女の人が) | ZH: "那個女人"
  Taro → EN: "the man"   | DE: "der Mann"     | JP: "男の人" (with particle が inside brackets: 男の人が) | ZH: "那個男人"

The character is ALWAYS the subject (NOM) in this file. Apply in all 4 language versions:
- Annotation lines 1–4 (EN / DE / JP / ZH)
- Answer line: e.g. (Emma). / (Emma). / (エマが). / (艾瑪). → (the girl). / (das Mädchen). / (女の子が). / (那個女孩).
- Question text (e.g. "does Emma give" → "does the girl give")
- Plain sentences at the end (capitalize at sentence start: "The girl gives…" / "Das Mädchen gibt…")

Japanese particle rule: the が particle stays INSIDE the NOM bracket — (女の子が), not (女の子)が.

FILE:
---
{content}
---

Output ONLY the rewritten file. No explanation, no markdown fences."""


def load_done() -> set[str]:
    if DONE_FILE.exists():
        return set(DONE_FILE.read_text("utf-8").splitlines())
    return set()


def mark_done(name: str):
    with _print_lock:
        with open(DONE_FILE, "a", encoding="utf-8") as f:
            f.write(name + "\n")


def has_named_char(text: str) -> bool:
    return any(ch in text for ch in NAMED_CHARS)


def verify_output(text: str) -> bool:
    """Basic format check: no named chars remain, has annotation brackets."""
    if has_named_char(text):
        return False
    if "(" not in text or "*" not in text:
        return False
    return True


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
    if content.startswith("```"):
        content = "\n".join(l for l in content.splitlines()
                            if not l.startswith("```")).strip()
    return content


def process_file(path: Path, api_key: str, dry_run: bool) -> tuple[str, bool, str]:
    """Returns (filename, success, error_msg)."""
    original = path.read_text("utf-8")

    if not has_named_char(original):
        return (path.name, True, "skipped (no named char)")

    prompt = PROMPT_TEMPLATE.format(content=original)
    try:
        result = call_api(prompt, api_key)
    except Exception as e:
        return (path.name, False, f"API error: {e}")

    if not verify_output(result):
        named_still = [c for c in NAMED_CHARS if c in result]
        return (path.name, False,
                f"verification failed — named chars still present: {named_still}")

    if not dry_run:
        path.write_text(result, "utf-8")

    return (path.name, True, "")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("ERROR: OPENROUTER_API_KEY not set")

    if args.dry_run:
        print("DRY RUN — files will be shown but not written\n")

    done = load_done()
    all_files = sorted(BRIDGE_DIR.glob("*.md"))
    pending = [f for f in all_files if f.name not in done]

    print(f"{len(all_files)} bridge files total, {len(done)} already done, "
          f"{len(pending)} to process")

    if not pending:
        print("Nothing to do.")
        return

    ok = fail = skip = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process_file, f, api_key, args.dry_run): f
                   for f in pending}
        for fut in as_completed(futures):
            name, success, msg = fut.result()
            with _print_lock:
                if msg.startswith("skipped"):
                    print(f"  SKIP  {name}")
                    skip += 1
                    if not args.dry_run:
                        mark_done(name)
                elif success:
                    print(f"  OK    {name}")
                    ok += 1
                    if not args.dry_run:
                        mark_done(name)
                else:
                    print(f"  FAIL  {name}: {msg}", file=sys.stderr)
                    fail += 1

    print(f"\nDone: {ok} rewritten, {skip} skipped, {fail} failed")
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
