#!/usr/bin/env python3
"""
angle_aug.py — Question-form augmentation pass over existing concept angle files.

Reads every file in training_data/redesign/words/, sends it to DeepSeek with
instructions to produce alternate-phrasing versions, writes new files alongside.

Three waves:
  --wave 1   Standard clean rephrasing (singular→plural, "what is" → "describe")
  --wave 2   Yes/no, negation, false-premise correction
  --wave 3   Messier natural chat phrasings

Usage:
  python3 meta/scripts/angle_aug.py gen --wave 1 [--workers 4] [--batch 100] [--source openrouter]
  python3 meta/scripts/angle_aug.py report

Auth: OPENROUTER_API_KEY / DEEPSEEK_API_KEY / NVIDIA_API_KEY (same as angle_gen.py)
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI, RateLimitError
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT   = Path(__file__).resolve().parent.parent.parent
WORDS_DIR   = REPO_ROOT / "training_data" / "redesign" / "words"
CLAIMS_DIR  = REPO_ROOT / "training_data" / "redesign" / "aug_claims"
DONE_FILE   = REPO_ROOT / "training_data" / "redesign" / "aug_done.txt"
FAILED_FILE = REPO_ROOT / "training_data" / "redesign" / "aug_failed.txt"
BASE_URL    = "https://openrouter.ai/api/v1"

SOURCES: dict[str, dict] = {
    "openrouter": {
        "base_url":    "https://openrouter.ai/api/v1",
        "model":       "deepseek/deepseek-v4-flash",
        "api_key_env": "OPENROUTER_API_KEY",
        "max_tokens":  8192,
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
        "max_tokens":  8192,
    },
}

RATE_LIMIT_WAITS = [60, 120, 300]
MAX_ATTEMPTS     = 2

_lock = threading.Lock()


def log(msg: str) -> None:
    with _lock:
        print(msg, flush=True)


def load_set(path: Path) -> set[str]:
    if path.exists():
        return set(path.read_text(encoding="utf-8").splitlines())
    return set()


def append_to(path: Path, entry: str) -> None:
    with _lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(entry + "\n")


def try_claim(key: str) -> bool:
    CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    safe = key.replace("/", "_").replace(" ", "_")
    try:
        (CLAIMS_DIR / f"{safe}.claim").open("x").close()
        return True
    except FileExistsError:
        return False


def release_claim(key: str) -> None:
    safe = key.replace("/", "_").replace(" ", "_")
    try:
        (CLAIMS_DIR / f"{safe}.claim").unlink()
    except FileNotFoundError:
        pass


# ── Prompts per wave ──────────────────────────────────────────────────────────

WAVE_PROMPTS: dict[int, str] = {
    1: """\
You are generating training data for Ninereeds, a small AI learning to understand language.

Below is an existing training file. Your task: produce exactly 1 alternate-phrasing version of it.

CRITICAL RULES — read carefully:
- Rephrase ONLY the [user] question. Use a different question surface: singular↔plural, "what is" → "describe", "what does X do" → "what can X do?", "tell me about X", "can you tell me about X", etc.
- Copy the [Ninereeds] answer almost exactly. The ONLY allowed change is grammar agreement: if the question shifts to plural, change "A dog is" → "Dogs are", "A dog has" → "Dogs have", etc.
- Do NOT restructure, reorder, or rephrase the answer sentences.
- Do NOT use pronouns (it, its, they, them). Every sentence must use the concept name as subject, just like the original.
- Do NOT add new facts. Do NOT remove facts.
- One output file only.
- Output filename: originalname_rephrase.md (e.g. dog_appearance.md → dog_appearance_rephrase.md).
- Format: === FILE: originalname_rephrase.md === then content.

Original file ({filename}):
{content}
""",

    2: """\
You are generating training data for Ninereeds, a small AI learning to understand language.

Below is an existing training file about a concept. Your task: produce yes/no and negation
files based on the facts stated in the original.

Rules:
- Yes/no questions: "does X have Y?" → "Yes. X has Y." or "No. X does not have Y. X has Z."
- False-premise correction: "is X a [wrong category]?" → "No. X is not a [wrong]. X is a [right]."
- One question per file.
- Answers: 1-3 sentences maximum.
- Generate 3-4 files total: mix of true-yes, true-no, and false-premise.
- Format: === FILE: originalname_yn1.md === then content, etc.

Original file ({filename}):
{content}
""",

    3: """\
You are generating training data for Ninereeds, a small AI learning to understand language.

Below is an existing training file. Your task: produce 1-2 versions using messier, more
natural chat phrasings — the kind a real person might type in a chat window.

Rules:
- Natural, slightly informal: "so what's a dog?", "dogs are what exactly?", "explain dogs to me"
- Same factual content in the answer, rephrased naturally.
- Answers stay short: 1-4 sentences.
- Do not use slang or contractions that would be hard to parse.
- One question form per file.
- Format: === FILE: originalname_c2.md === then content, etc.

Original file ({filename}):
{content}
""",
}


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


def augment_file(client: OpenAI, src_file: Path, wave: int,
                 max_tokens: int, source: str) -> bool:
    content  = src_file.read_text(encoding="utf-8")
    prompt   = WAVE_PROMPTS[wave].format(filename=src_file.name, content=content)
    attempts = 0
    rate_hits = 0

    while attempts < MAX_ATTEMPTS:
        try:
            resp = client.chat.completions.create(
                model=client.model,  # type: ignore[attr-defined]
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            raw    = resp.choices[0].message.content or ""
            reason = resp.choices[0].finish_reason

            if reason == "length":
                log(f"  WARN [{source}:{src_file.name}] truncated")

            files = parse_files(raw)
            if not files:
                log(f"  WARN [{source}:{src_file.name}] no files parsed (attempt {attempts+1})")
                attempts += 1
                continue

            bad = [fn for fn, c in files.items() if not validate(c)]
            if bad:
                log(f"  WARN [{source}:{src_file.name}] invalid {bad} (attempt {attempts+1})")
                attempts += 1
                continue

            out_dir = src_file.parent
            for fname, fc in files.items():
                (out_dir / fname).write_text(fc + "\n", encoding="utf-8")

            log(f"  OK   [{source}] {src_file.name} → {len(files)} aug files")
            return True

        except RateLimitError:
            if rate_hits >= len(RATE_LIMIT_WAITS):
                log(f"  FAIL [{source}:{src_file.name}] too many rate limits")
                return False
            wait = RATE_LIMIT_WAITS[rate_hits]
            rate_hits += 1
            log(f"  RATE [{source}:{src_file.name}] 429 — waiting {wait}s")
            time.sleep(wait)

        except Exception as e:
            log(f"  ERR  [{source}:{src_file.name}] {e} (attempt {attempts+1})")
            attempts += 1

    return False


def build_queue(wave: int, done: set[str], failed: set[str]) -> list[Path]:
    """Find source files that haven't been augmented for this wave yet."""
    skip = done | failed
    aug_suffixes = ("_rephrase", "_v2", "_v3", "_v4", "_yn", "_c2", "_c3")

    # Scan bucket-by-bucket with os.listdir (avoids deep recursive traversal
    # on USB drives where one big find can stall in kernel disk-wait)
    raw: list[Path] = []
    for bucket in sorted(os.listdir(str(WORDS_DIR))):
        bucket_path = WORDS_DIR / bucket
        if not os.path.isdir(str(bucket_path)):
            continue
        for fname in os.listdir(str(bucket_path)):
            if fname.endswith(".md"):
                raw.append(bucket_path / fname)
    all_files = sorted(raw)

    queue: list[Path] = []
    for f in all_files:
        if any(f.stem.endswith(s) for s in aug_suffixes):
            continue
        key = f"{wave}:{f.relative_to(WORDS_DIR)}"
        if key not in skip:
            queue.append(f)

    return queue


def cmd_gen(args: argparse.Namespace) -> None:
    cfg     = SOURCES[args.source]
    model   = args.model or cfg["model"]
    api_key = os.environ.get(cfg["api_key_env"], "")
    if not api_key:
        print(f"ERROR: {cfg['api_key_env']} not set.", file=sys.stderr)
        sys.exit(1)

    done   = load_set(DONE_FILE)
    failed = load_set(FAILED_FILE) if not args.retry_failed else set()
    queue  = build_queue(args.wave, done, failed)
    if args.batch:
        queue = queue[:args.batch]

    print(f"[{args.source}] wave {args.wave} | {len(queue)} files to augment | model: {model}")
    if not queue:
        print("Nothing to do.")
        return

    client       = OpenAI(api_key=api_key, base_url=cfg["base_url"])
    client.model = model  # type: ignore[attr-defined]

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures: dict = {}
        for f in queue:
            key = f"{args.wave}:{f.relative_to(WORDS_DIR)}"
            if not try_claim(key):
                continue
            futures[pool.submit(augment_file, client, f, args.wave,
                                cfg["max_tokens"], args.source)] = (f, key)

        for fut in as_completed(futures):
            f, key = futures[fut]
            rel    = str(f.relative_to(WORDS_DIR))
            if fut.result():
                append_to(DONE_FILE, f"{args.wave}:{rel}")
            else:
                append_to(FAILED_FILE, f"{args.wave}:{rel}")
            release_claim(key)


def cmd_report(_args: argparse.Namespace) -> None:
    done   = load_set(DONE_FILE)
    failed = load_set(FAILED_FILE)
    aug_sfx = ("_rephrase", "_v2", "_v3", "_v4", "_yn", "_c2", "_c3")
    result = subprocess.run(
        ["find", str(WORDS_DIR), "-name", "*.md", "-type", "f"],
        capture_output=True, text=True
    )
    all_files = [Path(p) for p in result.stdout.splitlines() if p.strip()]
    total = sum(1 for f in all_files if not any(f.stem.endswith(s) for s in aug_sfx))
    rephrase_done = sum(1 for f in all_files if f.stem.endswith("_rephrase"))

    print(f"Source files:       {total}")
    print(f"Rephrase files:     {rephrase_done}")
    print(f"Aug done (tracked): {len(done)}")
    print(f"Aug failed:         {len(failed)}")
    print(f"Total files:        {len(all_files)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Question-form augmentation for concept files")
    sub    = parser.add_subparsers(dest="cmd")

    g = sub.add_parser("gen")
    g.add_argument("--wave",         type=int, choices=[1,2,3], required=True)
    g.add_argument("--source",       choices=list(SOURCES), default="openrouter")
    g.add_argument("--model",        default=None)
    g.add_argument("--workers",      type=int, default=4)
    g.add_argument("--batch",        type=int, default=None)
    g.add_argument("--retry-failed", action="store_true")

    sub.add_parser("report")

    args = parser.parse_args()
    if args.cmd == "gen":
        cmd_gen(args)
    elif args.cmd == "report":
        cmd_report(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
