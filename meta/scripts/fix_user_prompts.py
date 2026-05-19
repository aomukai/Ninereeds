#!/usr/bin/env python3
"""
Fix English-in-[user]-line bugs in DE/JP/ZH triplet story files.

For each file: reads the broken file + its EN counterpart, asks DeepSeek to
rewrite the [user] line into the correct target language. Body is preserved
unless there are structural artifacts (merged lines, editorial notes), which
DeepSeek cleans up using the EN file as reference.

Language is detected from the filename suffix: _DE.md / _JP.md / _ZH.md.

Queue:    tmp/multilang_user_fix_queue.txt  (absolute paths, one per line)
Progress: tmp/multilang_user_fix_done.txt   (completed absolute paths)

Usage:
  python3 meta/scripts/fix_user_prompts.py [--batch 50] [--workers 8] [--dry-run]
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

QUEUE_FILE = pathlib.Path("tmp/multilang_user_fix_queue.txt")
DONE_FILE  = pathlib.Path("tmp/multilang_user_fix_done.txt")

SYSTEM_MSG = (
    "You are a corpus repair tool. Output ONLY the corrected file contents. "
    "No markdown fences, no commentary, no explanations."
)

LANG_CONFIG = {
    "DE": {
        "name": "German",
        "phrasing_hint": (
            'e.g. „Erzähl mir eine Geschichte über …", '
            '„Ich möchte eine Geschichte über … hören.", '
            '„Erzähl mir von …" — vary it naturally.'
        ),
        "loan_hint": (
            "For abstract or technical terms, use natural German — native words, "
            "established loanwords, or a mix, whichever sounds most idiomatic."
        ),
    },
    "JP": {
        "name": "Japanese",
        "phrasing_hint": (
            "e.g. 「〇〇の話をして。」「〇〇の話を聞かせて。」"
            "「〇〇について話して？」「〇〇の話を聞かせてくれる？」 — vary naturally."
        ),
        "loan_hint": (
            "For abstract or loan-word concepts, pick the most natural option — "
            "native Japanese, katakana, or a mix — based on the story context."
        ),
    },
    "ZH": {
        "name": "Mandarin Chinese",
        "phrasing_hint": (
            'e.g. "给我讲一个关于〇〇的故事。" "跟我说说〇〇的故事吧。" '
            '"讲一个〇〇的故事给我听。" — vary it naturally.'
        ),
        "loan_hint": (
            "Use natural Mandarin Chinese. The [user] line must contain no English "
            "letters — all text must be in Chinese characters."
        ),
    },
}

PROMPT_TMPL = """\
This is a {lang_name} story file from a language training corpus. Fix it \
according to the rules below.

## Problem
The [user] line contains English text or a mix of English and {lang_name}. \
Rewrite it into natural {lang_name}.

## Rules
- Rewrite ONLY the [user] line. Do not retranslate or rewrite the [Ninereeds] story.
- Choose the most natural {lang_name} phrasing for the topic. {phrasing_hint}
- {loan_hint}
- If the [Ninereeds] body has obvious structural artifacts — lines merged without \
a newline, or English editorial notes — clean those up too, using the EN reference \
to stay faithful to the story. Do not otherwise alter the body.
- The output must be exactly two non-empty lines: one [user] line, one [Ninereeds] line.

## EN reference (same story — use for topic and context only):
{en_content}

## Broken {lang_name} file to fix:
{file_content}
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


def detect_lang(p: pathlib.Path) -> str:
    for lang in ("DE", "JP", "ZH"):
        if p.name.endswith(f"_{lang}.md"):
            return lang
    raise ValueError(f"Cannot detect language from filename: {p.name}")


def en_path(p: pathlib.Path, lang: str) -> pathlib.Path:
    return p.with_name(p.name.replace(f"_{lang}.md", "_EN.md"))


def has_english_user_line(content: str) -> bool:
    for line in content.splitlines():
        if line.startswith("[user]"):
            body = line[len("[user]"):]
            if re.search(r"[a-zA-Z]", body):
                return True
    return False


def verify(content: str, lang: str) -> tuple[bool, str]:
    lines = [l for l in content.splitlines() if l.strip()]
    user_lines = [l for l in lines if l.startswith("[user]")]
    nine_lines = [l for l in lines if l.startswith("[Ninereeds]")]
    if not user_lines:
        return False, "missing [user] line"
    if not nine_lines:
        return False, "missing [Ninereeds] line"
    body = user_lines[0][len("[user]"):]
    if lang in ("JP", "ZH"):
        if re.search(r"[a-zA-Z]", body):
            return False, f"English still present: {body[:60]}"
    else:  # DE — just check it's no longer a plain English "tell me" prompt
        if re.search(r"^tell me\b", body, re.IGNORECASE):
            return False, f"Still English: {body[:60]}"
    return True, "OK"


def fix_one(p: pathlib.Path, client: OpenAI, dry_run: bool) -> bool:
    try:
        lang    = detect_lang(p)
        cfg     = LANG_CONFIG[lang]
        content = p.read_text()
        en      = en_path(p, lang)
        en_content = en.read_text() if en.exists() else "(EN file not found)"

        if dry_run:
            _log(f"  [DRY RUN] [{lang}] {p.name}")
            return True

        prompt = PROMPT_TMPL.format(
            lang_name=cfg["name"],
            phrasing_hint=cfg["phrasing_hint"],
            loan_hint=cfg["loan_hint"],
            en_content=en_content.strip(),
            file_content=content.strip(),
        )

        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_MSG},
                {"role": "user",   "content": prompt},
            ],
            max_tokens=4096,
        )

        result = (resp.choices[0].message.content or "").strip()

        if result.startswith("```"):
            result = result.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        ok, reason = verify(result, lang)
        if not ok:
            _log(f"  FAIL [{lang}] {p.name}: {reason}")
            return False

        p.write_text(result + "\n")
        tok_in  = resp.usage.prompt_tokens     if resp.usage else "?"
        tok_out = resp.usage.completion_tokens if resp.usage else "?"
        _log(f"  OK   [{lang}] {p.name} ({tok_in}→{tok_out})")
        return True

    except Exception as e:
        _log(f"  ERROR {p.name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Fix English [user] lines in DE/JP/ZH files")
    parser.add_argument("--batch",   type=int, default=50)
    parser.add_argument("--workers", type=int, default=8)
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

    ok        = sum(1 for _, s in results if s)
    fail      = sum(1 for _, s in results if not s)
    remaining = len(queue) - ok

    print()
    print("RECEIPT")
    print("-------")
    print(f"Processed: {len(batch)}  OK: {ok}  Failed: {fail}")
    print(f"Remaining: {remaining}")
    print(f"Status: {'DONE' if remaining == 0 else 'IN_PROGRESS'}")


if __name__ == "__main__":
    main()
