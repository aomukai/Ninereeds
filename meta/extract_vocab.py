#!/usr/bin/env python3
"""
Vocabulary extraction worker — direct OpenRouter API, no opencode dependency.

For each file in the queue, sends content to DeepSeek v4 flash and asks it to
extract and normalise verbs, adjectives, and nouns. Merges results (deduped,
sorted) into three output files. Resumable via a progress ledger.

Usage:
  python3 meta/extract_vocab.py --queue training_data/wiki/files.txt
  python3 meta/extract_vocab.py --queue training_data/wiki/files.txt --workers 4
  python3 meta/extract_vocab.py --queue training_data/wiki/files.txt --dry-run

Output files are written alongside the queue file:
  <queue_dir>/nouns.txt
  <queue_dir>/verbs.txt
  <queue_dir>/adjectives.txt
  <queue_dir>/files_done.txt   ← progress ledger

Auth:
  Set OPENROUTER_API_KEY env var (or OPENAI_API_KEY as fallback).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import threading
import urllib.error
import urllib.request
from pathlib import Path

OPENROUTER_URL = "https://openrouter.ai/api/v1"
MODEL = "deepseek/deepseek-v4-flash"

PRINT_LOCK = threading.Lock()
MERGE_LOCK = threading.Lock()

EXTRACTION_PROMPT = """\
Extract content words from the text below into three groups.

Rules:
- Ignore speaker tags: [user] [Ninereeds]
- Ignore numbers and proper names.
- Ignore function/grammar words (articles, prepositions, conjunctions, auxiliaries).
- Ignore temporal/spatial words: now, then, here, there, before, after, above, below, inside, outside, already, still, just, always, never, often, sometimes.
- Keep only meaningful content words.

Normalise:
- Verbs: base/infinitive form. (thinking → think, became → become, runs → run)
- Adjectives: drop adverb suffix where clear, then dictionary form. (clearly → clear, slowly → slow, bigger → big)
- Nouns: singular form. (patterns → pattern, systems → system)

Output exactly this format — no headings, no commentary, no blank lines within a section:

VERBS:
<one verb per line>

ADJECTIVES:
<one adjective per line>

NOUNS:
<one noun per line>

Text to process:
---
{content}
---
"""


def get_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    return key


def log(msg: str) -> None:
    with PRINT_LOCK:
        print(msg, flush=True)


def call_api(content: str, timeout: int) -> str:
    import time, json
    from openai import OpenAI
    client = OpenAI(api_key=get_api_key(), base_url=OPENROUTER_URL)
    prompt = EXTRACTION_PROMPT.format(content=content)
    last_exc: Exception | None = None
    for attempt in range(3):
        if attempt:
            time.sleep(15 * attempt)
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=65536,  # thinking model: 32k was too small, reasoning tokens fill budget and truncate output
                temperature=0.1,
                timeout=timeout,
            )
            text = (resp.choices[0].message.content or "").strip()
            if text:
                return text
        except (json.JSONDecodeError, Exception) as exc:
            last_exc = exc
            log(f"  retry {attempt+1}/3 after error: {exc}")
            continue
    raise RuntimeError(f"API failed after 3 attempts: {last_exc}")


def parse_response(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {"verbs": [], "adjectives": [], "nouns": []}
    current: str | None = None

    # Strip thinking blocks (<think>...</think> or similar)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    for line in text.splitlines():
        # Strip markdown formatting and whitespace
        stripped = re.sub(r"[*_`#]", "", line).strip().upper()

        if re.match(r"^VERBS\s*:?$", stripped):
            current = "verbs"
        elif re.match(r"^ADJECTIVES?\s*:?$", stripped) or re.match(r"^ADVERBS?\s*:?$", stripped):
            current = "adjectives"
        elif re.match(r"^NOUNS?\s*:?$", stripped):
            current = "nouns"
        elif stripped and current:
            # Accept comma-separated lines too (model sometimes bundles words)
            raw = line.strip().lower()
            for word in re.split(r"[,;\s]+", raw):
                word = word.strip().strip(".-")
                if re.match(r"^[a-z][a-z\-]{1,30}$", word):
                    result[current].append(word)

    return result


def merge_into(output_file: Path, new_words: list[str]) -> int:
    with MERGE_LOCK:
        existing: set[str] = set()
        if output_file.exists():
            existing = {w.strip() for w in output_file.read_text(encoding="utf-8").splitlines() if w.strip()}
        combined = sorted(existing | set(new_words))
        output_file.write_text("\n".join(combined) + "\n", encoding="utf-8")
        return len(combined) - len(existing)


def mark_done(progress_file: Path, file_path: str) -> None:
    with MERGE_LOCK:
        with progress_file.open("a", encoding="utf-8") as fh:
            fh.write(file_path + "\n")


def process_file(
    file_path: str,
    out_dir: Path,
    timeout: int,
    dry_run: bool,
) -> tuple[bool, str]:
    try:
        content = Path(file_path).read_text(encoding="utf-8", errors="replace")
        if dry_run:
            log(f"[DRY RUN] {file_path}")
            return True, "dry-run"

        response = call_api(content, timeout)
        words = parse_response(response)

        if not any(words.values()):
            debug_dir = Path("tmp/extract_vocab_debug")
            debug_dir.mkdir(parents=True, exist_ok=True)
            (debug_dir / (Path(file_path).stem + ".txt")).write_text(response, encoding="utf-8")
            raise RuntimeError("parsed no words from response (raw saved to tmp/extract_vocab_debug/)")

        total = sum(len(v) for v in words.values())
        for cat, lst in words.items():
            if total > 20 and len(lst) / total > 0.95:
                raise RuntimeError(f"implausible output: {len(lst)}/{total} words all in {cat}")

        added_v = merge_into(out_dir / "verbs.txt", words["verbs"])
        added_a = merge_into(out_dir / "adjectives.txt", words["adjectives"])
        added_n = merge_into(out_dir / "nouns.txt", words["nouns"])
        mark_done(out_dir / "files_done.txt", file_path)

        log(f"OK  {Path(file_path).name}  +{added_v}v +{added_a}adj +{added_n}n")
        return True, "ok"

    except Exception as exc:
        log(f"FAIL {Path(file_path).name}: {exc}")
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract vocabulary from corpus files via DeepSeek API")
    parser.add_argument("--queue", required=True, help="Path to files.txt queue")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    queue_file = Path(args.queue)
    if not queue_file.exists():
        raise SystemExit(f"Queue not found: {queue_file}")

    out_dir = queue_file.parent
    progress_file = out_dir / "files_done.txt"

    all_files = [l.strip() for l in queue_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    done = set()
    if progress_file.exists():
        done = {l.strip() for l in progress_file.read_text(encoding="utf-8").splitlines() if l.strip()}

    pending = [f for f in all_files if f not in done]
    log(f"Queue: {len(all_files)} total, {len(done)} done, {len(pending)} pending")
    log(f"Workers: {args.workers}  Timeout: {args.timeout}s  Output: {out_dir}")

    if not pending:
        log("Nothing to do.")
        return 0

    succeeded = 0
    failed = 0
    workers = 1 if args.dry_run else max(1, min(args.workers, len(pending)))

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(process_file, f, out_dir, args.timeout, args.dry_run): f
            for f in pending
        }
        for future in concurrent.futures.as_completed(futures):
            ok, _ = future.result()
            if ok:
                succeeded += 1
            else:
                failed += 1

    done_now = succeeded + len(done)
    print()
    print("RECEIPT")
    print("-------")
    print(f"Processed this run : {succeeded} ok, {failed} failed")
    print(f"Total done         : {done_now} / {len(all_files)}")
    print(f"Remaining          : {len(all_files) - done_now}")
    print(f"Status             : {'DONE' if done_now == len(all_files) else 'IN_PROGRESS'}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
