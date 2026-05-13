#!/usr/bin/env python3
"""
Multilingual lang_1 file generator.

Reads inventory/allowlist.txt, determines which words don't have
lang_1 files yet, batches them 10 at a time, sends to DeepSeek V4 Flash
via OpenRouter, parses the JSON response, and writes the files.

Usage:
  python3 meta/scripts/lang_gen.py [--batch 10] [--workers 4] [--dry-run]

Auth (same priority order as CLAUDE.md):
  1. OPENROUTER_API_KEY env var
  2. OPENAI_API_KEY env var
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
import threading
from pathlib import Path

from openai import OpenAI

# Force UTF-8 output so Japanese/Chinese in log lines don't crash on Windows cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT   = Path(__file__).resolve().parent.parent.parent
ALLOWLIST   = REPO_ROOT / "inventory/allowlist.txt"
PROMPT_TPL  = REPO_ROOT / "training_data/lang/prompt.md"
OUTPUT_DIR  = REPO_ROOT / "training_data/lang/lang_1"
BASE_URL    = "https://openrouter.ai/api/v1"
MODEL       = "deepseek/deepseek-v4-flash"

_print_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def load_api_key() -> str:
    for var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        if key := os.environ.get(var):
            return key
    return ""


def word_to_filename(word: str) -> str:
    """Convert allowlist word to output filename (spaces→underscores, hyphens kept)."""
    return word.strip().replace(" ", "_") + ".md"


def load_pending_words() -> list[str]:
    """Return allowlist words that don't have a lang_1 file yet."""
    words = [
        line.strip()
        for line in ALLOWLIST.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    pending = []
    for word in words:
        fname = word_to_filename(word)
        if not (OUTPUT_DIR / fname).exists():
            pending.append(word)
    return pending


def build_prompt(template: str, words: list[str]) -> str:
    """Replace <word N> placeholders with actual words; strip the file-read instruction."""
    prompt = template
    # Remove the opencode-specific file read instruction
    prompt = re.sub(r"Read training_data/allowlist\.txt\.\n?", "", prompt)
    for i, word in enumerate(words, 1):
        prompt = prompt.replace(f"<word {i}>", word)
    return prompt


def parse_response(text: str) -> list[dict] | None:
    """Extract and parse the JSON object from model output."""
    # Strip markdown fences if present
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[^\n]*\n", "", text)
        text = re.sub(r"\n?```$", "", text)
    # Find the JSON object
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
        return data.get("files", [])
    except json.JSONDecodeError:
        return None


def process_batch(
    words: list[str],
    template: str,
    client: OpenAI,
    dry_run: bool,
) -> tuple[list[str], list[str]]:
    """
    Send one batch to the API and write resulting files.
    Returns (written_words, failed_words).
    """
    prompt = build_prompt(template, words)

    if dry_run:
        log(f"  [DRY-RUN] batch: {words}")
        return words, []

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192,
        )
    except Exception as e:
        log(f"  API ERROR for batch {words[0]}…: {e}")
        return [], words

    raw = resp.choices[0].message.content or ""
    tokens_in  = resp.usage.prompt_tokens if resp.usage else "?"
    tokens_out = resp.usage.completion_tokens if resp.usage else "?"

    files = parse_response(raw)
    if files is None:
        log(f"  PARSE FAIL for batch {words[0]} ({tokens_in}->{tokens_out}) raw:\n{raw[:300]}")
        return [], words

    written, failed = [], []
    expected = {w.strip().lower(): w for w in words}

    for item in files:
        word      = item.get("word", "").strip()
        filename  = item.get("filename", "").strip()
        lines     = item.get("lines", [])

        if not filename:
            filename = word_to_filename(word)

        if len(lines) != 4 or not all(lines):
            log(f"  SKIP {filename}: expected 4 lines, got {len(lines)}")
            failed.append(word)
            continue

        out_path = OUTPUT_DIR / filename
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # Verify write
        readback = out_path.read_text(encoding="utf-8").strip().splitlines()
        if len(readback) != 4:
            log(f"  VERIFY FAIL {filename}")
            failed.append(word)
        else:
            log(f"  OK {filename} ({tokens_in}->{tokens_out})")
            written.append(word)

    # Any words in the batch not returned by the model
    returned_words = {item.get("word", "").strip().lower() for item in files}
    for word in words:
        if word.lower() not in returned_words and word not in failed and word not in written:
            log(f"  MISSING from response: {word}")
            failed.append(word)

    return written, failed


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate lang_1 multilingual files")
    parser.add_argument("--batch",   type=int,  default=10,    help="Words per API call")
    parser.add_argument("--workers", type=int,  default=4,     help="Parallel API workers")
    parser.add_argument("--limit",   type=int,  default=0,     help="Max words to process (0=all)")
    parser.add_argument("--dry-run", action="store_true",      help="Don't write files")
    args = parser.parse_args()

    api_key = load_api_key()
    if not api_key:
        print("ERROR: set OPENROUTER_API_KEY or OPENAI_API_KEY", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    template = PROMPT_TPL.read_text(encoding="utf-8")
    pending  = load_pending_words()

    if args.limit:
        pending = pending[: args.limit]

    total = len(pending)
    if total == 0:
        print("Nothing to do — all allowlist words have lang_1 files.")
        return

    print(f"Pending: {total} words | batch={args.batch} workers={args.workers}")

    # Slice into batches
    batches = [pending[i : i + args.batch] for i in range(0, total, args.batch)]
    print(f"Batches: {len(batches)}")

    all_failed: list[str] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(process_batch, batch, template, client, args.dry_run): batch
            for batch in batches
        }
        for fut in concurrent.futures.as_completed(futures):
            written, failed = fut.result()
            if failed:
                all_failed.extend(failed)

    done = total - len(all_failed)
    print(f"\nDone: {done}/{total} written. Failed: {len(all_failed)}")
    if all_failed:
        print("Failed words:", all_failed)


if __name__ == "__main__":
    main()
