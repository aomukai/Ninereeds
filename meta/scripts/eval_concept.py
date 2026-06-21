#!/usr/bin/env python3
"""
eval_concept.py — Conversational concept comprehension eval for Ninereeds.

Samples random words from the concept corpus, asks varied questions using
phrasing DIFFERENT from the training files, and logs what comes back.
The goal is comprehension, not grammar: does it know what a dog is?
Does it talk about Rome when asked if a dog is an animal?

Usage:
  python3 meta/scripts/eval_concept.py [--checkpoint path/to/model.pt]
                                        [--words 30]
                                        [--buckets animals,body,food]
                                        [--seed 42]

Output: tmp/eval_concept_TIMESTAMP.log
        (also printed to console as it runs)

Auto-flags obvious failures:
  ROME    — response mentions Rome or Russia (known hallucination)
  FOREIGN — non-Latin characters in response (language bleed)
  EMPTY   — response too short to be meaningful
  ECHO    — response just repeats the question word with no content
"""

from __future__ import annotations

import argparse
import datetime
import os
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Question templates ────────────────────────────────────────────────────────
# Deliberately different phrasing from training angle files.
# {w} = word, {W} = capitalised word

QUESTIONS: dict[str, list[str]] = {
    "general": [
        "tell me about {w}",
        "what do you know about {w}?",
        "can you describe {w}?",
        "what can you tell me about {w}?",
        "describe {w} to me",
    ],
    "classification": [
        "what kind of thing is a {w}?",
        "is {w} a living thing?",
        "is a {w} an animal, an object, or something else?",
        "would you call {w} a thing or an action?",
    ],
    "property": [
        "what does a {w} look like?",
        "what are some properties of {w}?",
        "what makes something a {w}?",
    ],
    "context": [
        "where would you find a {w}?",
        "when do you see a {w}?",
        "who uses {w}?",
    ],
    "boundary": [
        "what is a {w} thinking right now?",
        "what is this specific {w}'s name?",
        "how many {w}s exist in the world?",
    ],
    "identity": [
        "who are you?",
        "what is your name?",
        "what can you do?",
        "do you know what a {w} is?",
    ],
}

# Per-bucket question emphasis
BUCKET_EMPHASIS: dict[str, list[str]] = {
    "animals":    ["general", "property", "context", "boundary"],
    "nature":     ["general", "property", "context", "boundary"],
    "household":  ["general", "property", "context", "boundary"],
    "food":       ["general", "property", "context", "boundary"],
    "body":       ["general", "property", "context", "boundary"],
    "people":     ["general", "classification", "context", "boundary"],
    "actions":    ["general", "classification", "boundary"],
    "properties": ["general", "classification", "boundary"],
    "space":      ["general", "classification", "boundary"],
    "time":       ["general", "classification", "boundary"],
    "unsorted":   ["general", "classification", "boundary"],
}


def pick_questions(word: str, bucket: str, n: int = 3) -> list[str]:
    categories = BUCKET_EMPHASIS.get(bucket, ["general", "classification", "boundary"])
    pool: list[str] = []
    for cat in categories:
        pool.extend(QUESTIONS.get(cat, []))
    random.shuffle(pool)
    seen: set[str] = set()
    chosen: list[str] = []
    for q in pool:
        rendered = q.format(w=word, W=word.capitalize())
        if rendered not in seen:
            seen.add(rendered)
            chosen.append(rendered)
        if len(chosen) >= n:
            break
    return chosen


# ── Failure flags ─────────────────────────────────────────────────────────────

HALLUCINATION_WORDS = {"rome", "russia", "moscow", "berlin", "russia", "empire", "soviet"}

def flag(response: str, word: str) -> list[str]:
    flags: list[str] = []
    r = response.lower()
    if len(response.strip()) < 8:
        flags.append("EMPTY")
    if any(h in r for h in HALLUCINATION_WORDS):
        flags.append("ROME")
    if re.search(r"[　-鿿가-퟿]", response):
        flags.append("FOREIGN")
    # Echo: response is just the word repeated with little else
    words_in_response = set(re.findall(r"\b\w+\b", r))
    if words_in_response <= {word.lower(), "a", "an", "the", "is", "are"}:
        flags.append("ECHO")
    return flags


# ── Word sampling ─────────────────────────────────────────────────────────────

def sample_words(words_dir: Path, done_file: Path,
                 n: int, buckets: list[str] | None,
                 seed: int) -> list[tuple[str, str]]:
    """Returns list of (word, bucket) tuples."""
    random.seed(seed)
    done: set[str] = set()
    if done_file.exists():
        done = set(done_file.read_text(encoding="utf-8").splitlines())

    # Build word→bucket mapping from directory structure
    word_bucket: dict[str, str] = {}
    if words_dir.exists():
        for bucket_dir in words_dir.iterdir():
            if not bucket_dir.is_dir():
                continue
            bname = bucket_dir.name
            if buckets and bname not in buckets:
                continue
            for f in bucket_dir.glob("*.md"):
                # filename: word_anglename.md → extract word (part before first _)
                word = f.stem.split("_")[0]
                word_bucket[word] = bname

    # Filter to done words only
    candidates = [(w, b) for w, b in word_bucket.items() if w in done]
    if not candidates:
        # Fall back: just sample from done list
        candidates = [(w, "unsorted") for w in done]

    random.shuffle(candidates)

    # If buckets specified, try to sample evenly across them
    if buckets:
        per_bucket = max(1, n // len(buckets))
        result: list[tuple[str, str]] = []
        by_bucket: dict[str, list[tuple[str, str]]] = {}
        for w, b in candidates:
            by_bucket.setdefault(b, []).append((w, b))
        for b in buckets:
            result.extend(by_bucket.get(b, [])[:per_bucket])
        return result[:n]

    return candidates[:n]


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Ninereeds concept comprehension eval")
    parser.add_argument("--checkpoint", default=str(ROOT / "chat" / "ninereeds.pt"))
    parser.add_argument("--words",   type=int, default=30, help="words to sample")
    parser.add_argument("--buckets", default=None,
                        help="comma-separated bucket names to sample from (default: all)")
    parser.add_argument("--seed",    type=int, default=42)
    parser.add_argument("--questions-per-word", type=int, default=3, dest="qpw")
    args = parser.parse_args()

    buckets = [b.strip() for b in args.buckets.split(",")] if args.buckets else None

    # Lazy import — only needed at runtime, not at import time
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
    from inference import BDHInference

    words_dir  = ROOT / "training_data" / "redesign" / "words"
    done_file  = ROOT / "training_data" / "redesign" / "words_done.txt"
    ckpt       = Path(args.checkpoint)
    ts         = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path   = ROOT / "tmp" / f"eval_concept_{ts}.log"
    log_path.parent.mkdir(exist_ok=True)

    sample = sample_words(words_dir, done_file, args.words, buckets, args.seed)
    if not sample:
        print("No words available. Run angle_gen first.")
        sys.exit(1)

    print(f"Loading {ckpt.name} ...")
    model = BDHInference(ckpt, max_new_tokens=120, temperature=0.3)

    header = (f"eval_concept  {ts}\n"
              f"checkpoint:   {ckpt.name}\n"
              f"words:        {len(sample)}\n"
              f"{'─' * 60}\n")
    print(header)

    lines: list[str] = [header]
    total_flags: dict[str, int] = {}

    for word, bucket in sample:
        questions = pick_questions(word, bucket, args.qpw)
        block = f"\n[{bucket}] {word}\n"
        print(block, end="")
        lines.append(block)

        for q in questions:
            prompt   = f"[user]{q}\n[Ninereeds]"
            response = model.generate_text(prompt)
            # Strip any follow-up turns
            for stop in ("\n[user]", "\n[Ninereeds]", "\n[User]"):
                if stop in response:
                    response = response[:response.index(stop)].strip()

            flags    = flag(response, word)
            flag_str = f"  [{', '.join(flags)}]" if flags else ""

            entry = f"  Q: {q}\n  A: {response}{flag_str}\n"
            print(entry, end="")
            lines.append(entry)
            for f_name in flags:
                total_flags[f_name] = total_flags.get(f_name, 0) + 1

    summary = (f"\n{'─' * 60}\n"
               f"words tested: {len(sample)}\n"
               f"flags:        {dict(total_flags) or 'none'}\n")
    print(summary)
    lines.append(summary)

    log_path.write_text("".join(lines), encoding="utf-8")
    print(f"log: {log_path}")


if __name__ == "__main__":
    main()
