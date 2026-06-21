#!/usr/bin/env python3
"""
angle_gen.py — Generate concept angle files for the Ninereeds redesign corpus.

Three API sources can run simultaneously. Each process claims words atomically
via a shared claims/ directory — whichever process creates the claim file first
owns that word. No two processes will generate the same word.

Usage (run each in a separate terminal):
  python3 meta/scripts/angle_gen.py gen --source openrouter [--workers 4] [--batch 100]
  python3 meta/scripts/angle_gen.py gen --source deepseek   [--workers 4] [--batch 100]
  python3 meta/scripts/angle_gen.py gen --source nvidia     [--workers 4] [--batch 100]

  python3 meta/scripts/angle_gen.py report
  python3 meta/scripts/angle_gen.py clean-claims   # remove stale claims from crashed runs

Auth — set the relevant env var before running each source:
  OPENROUTER_API_KEY
  DEEPSEEK_API_KEY
  NVIDIA_API_KEY

Output:  training_data/redesign/words/<bucket>/
Claims:  training_data/redesign/claims/   (transient — deleted on success)
Done:    training_data/redesign/words_done.txt
Failed:  training_data/redesign/words_failed.txt
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import time

from openai import OpenAI, RateLimitError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT   = Path(__file__).resolve().parent.parent.parent
BRIEF_PATH  = REPO_ROOT / "training_data" / "redesign" / "deepseek_brief.md"
WORD_LIST   = REPO_ROOT / "inventory" / "allowlist.txt"
WORDS_DIR   = REPO_ROOT / "training_data" / "redesign" / "words"
CLAIMS_DIR  = REPO_ROOT / "training_data" / "redesign" / "claims"
DONE_FILE   = REPO_ROOT / "training_data" / "redesign" / "words_done.txt"
FAILED_FILE = REPO_ROOT / "training_data" / "redesign" / "words_failed.txt"

# ── API source config ─────────────────────────────────────────────────────────

SOURCES: dict[str, dict] = {
    "openrouter": {
        "base_url":    "https://openrouter.ai/api/v1",
        "model":       "deepseek/deepseek-v4-flash",
        "api_key_env": "OPENROUTER_API_KEY",
        "max_tokens":  16384,   # thinking model — reasoning tokens eat headroom
    },
    "deepseek": {
        "base_url":    "https://api.deepseek.com",
        "model":       "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "max_tokens":  4096,
    },
    "nvidia": {
        "base_url":    "https://integrate.api.nvidia.com/v1",
        "model":       "deepseek-ai/deepseek-v4-flash",
        "api_key_env": "NVIDIA_API_KEY",
        "max_tokens":  16384,   # thinking model on NIM too
    },
}

# ── Bucket map ────────────────────────────────────────────────────────────────
# Words not listed here go to words/unsorted/. Add entries as buckets are defined.

BUCKETS: dict[str, str] = {
    # animals
    "dog": "animals", "cat": "animals", "bird": "animals", "fish": "animals",
    "horse": "animals", "rabbit": "animals", "bear": "animals", "wolf": "animals",
    "mouse": "animals", "deer": "animals",
    # nature
    "tree": "nature", "flower": "nature", "water": "nature", "fire": "nature",
    "stone": "nature", "earth": "nature", "sky": "nature", "sun": "nature",
    "moon": "nature", "rain": "nature", "wind": "nature", "river": "nature",
    "mountain": "nature",
    # household
    "table": "household", "chair": "household", "door": "household", "window": "household",
    "key": "household", "cup": "household", "bowl": "household", "book": "household",
    "rope": "household", "box": "household", "bag": "household", "bed": "household",
    "floor": "household", "wall": "household",
    # food
    "bread": "food", "apple": "food", "egg": "food", "milk": "food",
    "meat": "food", "salt": "food", "rice": "food", "soup": "food", "fruit": "food",
    # body
    "hand": "body", "eye": "body", "ear": "body", "nose": "body", "mouth": "body",
    "foot": "body", "head": "body", "arm": "body", "leg": "body", "face": "body",
    "teeth": "body", "hair": "body",
    # people
    "child": "people", "friend": "people", "family": "people", "teacher": "people",
    "mother": "people", "father": "people", "person": "people", "baby": "people",
    "man": "people", "woman": "people",
    # actions
    "run": "actions", "walk": "actions", "eat": "actions", "sleep": "actions",
    "look": "actions", "speak": "actions", "carry": "actions", "give": "actions",
    "take": "actions", "open": "actions", "close": "actions", "build": "actions",
    "fall": "actions", "hold": "actions",
    # properties
    "big": "properties", "small": "properties", "hot": "properties", "cold": "properties",
    "hard": "properties", "soft": "properties", "heavy": "properties", "light": "properties",
    "dark": "properties", "bright": "properties", "fast": "properties", "slow": "properties",
    "old": "properties", "new": "properties",
    # space
    "above": "space", "below": "space", "inside": "space", "outside": "space",
    "near": "space", "far": "space", "left": "space", "right": "space",
    "front": "space", "between": "space",
    # time
    "day": "time", "night": "time", "morning": "time", "before": "time",
    "after": "time", "now": "time",
}


def out_dir_for(word: str) -> Path:
    return WORDS_DIR / BUCKETS.get(word, "unsorted")


# ── Thread-safe logging ───────────────────────────────────────────────────────

_lock = threading.Lock()


def log(msg: str) -> None:
    with _lock:
        print(msg, flush=True)


# ── Progress files ────────────────────────────────────────────────────────────

def load_set(path: Path) -> set[str]:
    if path.exists():
        return set(path.read_text(encoding="utf-8").splitlines())
    return set()


def append_to(path: Path, word: str) -> None:
    with _lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(word + "\n")


def load_words(limit: int | None = None) -> list[str]:
    words = [w.strip() for w in WORD_LIST.read_text(encoding="utf-8").splitlines() if w.strip()]
    return words[:limit] if limit else words


# ── Claim mechanism ───────────────────────────────────────────────────────────

def try_claim(word: str) -> bool:
    """Atomically claim a word. Returns True if this process won the claim."""
    CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        (CLAIMS_DIR / f"{word}.claim").open("x").close()
        return True
    except FileExistsError:
        return False


def release_claim(word: str) -> None:
    """Release a claim so another source can retry the word."""
    claim = CLAIMS_DIR / f"{word}.claim"
    try:
        claim.unlink()
    except FileNotFoundError:
        pass


# ── Prompt ────────────────────────────────────────────────────────────────────

USER_PROMPT = """\
Generate the concept angle files for the word: **{word}**

Steps:
1. Identify the word type: concrete_noun, abstract, verb, or adjective.
2. Select only the angles that naturally fit this word. Skip any that don't apply.
3. Generate one file per angle using the file format from the brief.

Output each file using EXACTLY this delimiter (no other text between files):

=== FILE: {word}_ANGLENAME.md ===
[file content]

Replace ANGLENAME with a short descriptive slug, e.g.:
  what_is, appearance, behavior, location, function, meaning, example,
  boundary_internal, boundary_name, boundary_quantity

Do not add any text outside the file blocks.
"""


# ── Generation ────────────────────────────────────────────────────────────────

def parse_files(response: str) -> dict[str, str]:
    files = {}
    pattern = re.compile(r"=== FILE: ([^\n=]+\.md) ===\n(.*?)(?==== FILE:|$)", re.DOTALL)
    for m in pattern.finditer(response):
        fname   = m.group(1).strip()
        content = m.group(2).strip()
        if content:
            files[fname] = content
    return files


def validate(content: str) -> bool:
    return "[user]" in content and "[Ninereeds]" in content


RATE_LIMIT_WAITS = [60, 120, 300]   # seconds to wait on successive 429s
MAX_ATTEMPTS     = 2


def generate_word(client: OpenAI, brief: str, word: str, max_tokens: int,
                  source: str) -> bool:
    attempts         = 0
    rate_limit_count = 0

    while attempts < MAX_ATTEMPTS:
        try:
            resp = client.chat.completions.create(
                model=client.model,          # stored on client below
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": brief},
                    {"role": "user",   "content": USER_PROMPT.format(word=word)},
                ],
            )
            raw    = resp.choices[0].message.content or ""
            reason = resp.choices[0].finish_reason

            if reason == "length":
                log(f"  WARN [{source}:{word}] response truncated")

            files = parse_files(raw)
            if not files:
                log(f"  WARN [{source}:{word}] no files parsed (attempt {attempts + 1})")
                attempts += 1
                continue

            bad = [fn for fn, c in files.items() if not validate(c)]
            if bad:
                log(f"  WARN [{source}:{word}] invalid files {bad} (attempt {attempts + 1})")
                attempts += 1
                continue

            out_dir = out_dir_for(word)
            out_dir.mkdir(parents=True, exist_ok=True)
            for fname, content in files.items():
                (out_dir / fname).write_text(content + "\n", encoding="utf-8")

            log(f"  OK   [{source}:{word}] {len(files)} files → words/{BUCKETS.get(word, 'unsorted')}/")
            return True

        except RateLimitError:
            if rate_limit_count >= len(RATE_LIMIT_WAITS):
                log(f"  FAIL [{source}:{word}] too many rate limit hits, giving up")
                return False
            wait = RATE_LIMIT_WAITS[rate_limit_count]
            rate_limit_count += 1
            log(f"  RATE [{source}:{word}] 429 — waiting {wait}s (hit {rate_limit_count})")
            time.sleep(wait)
            # Rate limits don't count against attempt budget

        except Exception as e:
            log(f"  ERR  [{source}:{word}] {e} (attempt {attempts + 1})")
            attempts += 1

    log(f"  FAIL [{source}:{word}] giving up after {MAX_ATTEMPTS} attempts")
    return False


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_gen(args: argparse.Namespace) -> None:
    cfg = SOURCES[args.source]

    # Allow --model override
    model = args.model or cfg["model"]

    api_key = os.environ.get(cfg["api_key_env"], "")
    if not api_key:
        print(f"ERROR: {cfg['api_key_env']} not set.", file=sys.stderr)
        sys.exit(1)

    brief      = BRIEF_PATH.read_text(encoding="utf-8")
    words      = load_words(args.limit)
    done       = load_set(DONE_FILE)
    failed     = load_set(FAILED_FILE) if not args.retry_failed else set()
    skip       = done | failed

    # Queue: words not yet done or failed (claims handled per-word at runtime)
    queue = [w for w in words if w not in skip]
    if args.batch:
        queue = queue[:args.batch]

    print(f"[{args.source}] words: {len(words)} total | {len(done)} done | "
          f"{len(failed)} failed | {len(queue)} in queue | model: {model}")
    if not queue:
        print("Nothing to do.")
        return

    # Store model on client as a custom attr (avoids passing it through every call)
    client       = OpenAI(api_key=api_key, base_url=cfg["base_url"], timeout=120.0)
    client.model = model  # type: ignore[attr-defined]
    max_tokens   = cfg["max_tokens"]

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures: dict = {}
        for word in queue:
            if not try_claim(word):
                log(f"  SKIP [{args.source}:{word}] claimed by another source")
                continue
            futures[pool.submit(generate_word, client, brief, word, max_tokens, args.source)] = word

        for fut in as_completed(futures):
            word = futures[fut]
            if fut.result():
                append_to(DONE_FILE, word)
                release_claim(word)
            else:
                append_to(FAILED_FILE, word)
                release_claim(word)


def cmd_report(_args: argparse.Namespace) -> None:
    words   = load_words()
    done    = load_set(DONE_FILE)
    failed  = load_set(FAILED_FILE)
    claims  = list(CLAIMS_DIR.glob("*.claim")) if CLAIMS_DIR.exists() else []
    files   = list(WORDS_DIR.rglob("*.md"))   if WORDS_DIR.exists()  else []

    print(f"Words total:    {len(words)}")
    print(f"Done:           {len(done)}")
    print(f"Failed:         {len(failed)}")
    print(f"Active claims:  {len(claims)}")
    print(f"Files written:  {len(files)}")

    # Per-bucket breakdown
    if WORDS_DIR.exists():
        for bucket in sorted(p.name for p in WORDS_DIR.iterdir() if p.is_dir()):
            count = len(list((WORDS_DIR / bucket).glob("*.md")))
            print(f"  {bucket:15s} {count} files")

    remaining = [w for w in words if w not in done and w not in failed]
    if remaining:
        print(f"Next up:        {remaining[:10]}")


def cmd_clean_claims(_args: argparse.Namespace) -> None:
    """Remove claim files for words that aren't in-progress (stale from crashed runs)."""
    if not CLAIMS_DIR.exists():
        print("No claims directory.")
        return
    done    = load_set(DONE_FILE)
    removed = 0
    for claim in CLAIMS_DIR.glob("*.claim"):
        word = claim.stem
        if word in done:
            claim.unlink()
            removed += 1
        else:
            # Not done — might be stale. Remove it so other sources can retry.
            claim.unlink()
            removed += 1
    print(f"Removed {removed} stale claim files.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Ninereeds concept angle files")
    sub    = parser.add_subparsers(dest="cmd")

    g = sub.add_parser("gen", help="Generate files")
    g.add_argument("--source",        choices=list(SOURCES), required=True)
    g.add_argument("--model",         default=None,  help="override default model for source")
    g.add_argument("--workers",       type=int, default=4)
    g.add_argument("--batch",         type=int, default=None, help="max words this run")
    g.add_argument("--limit",         type=int, default=None, help="cap word list length")
    g.add_argument("--retry-failed",  action="store_true",   help="retry previously failed words")

    sub.add_parser("report",       help="Show progress")
    sub.add_parser("clean-claims", help="Remove stale claim files from crashed runs")

    args = parser.parse_args()
    if args.cmd == "gen":
        cmd_gen(args)
    elif args.cmd == "report":
        cmd_report(args)
    elif args.cmd == "clean-claims":
        cmd_clean_claims(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
