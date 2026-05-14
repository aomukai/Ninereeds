#!/usr/bin/env python3
"""
Phase backfill — generate phase corpus files for words missing from the allowlist.

Generates files following the exact Ninereeds phase format:
  4 [user]/[Ninereeds] pairs, 5 body lines + 1 summary each.
  No pronouns. No negation in body lines. Subject of every line is X.

Usage:
  python3 meta/scripts/phase_backfill.py [--dry-run]

Auth:
  1. OPENROUTER_API_KEY env var
  2. OPENAI_API_KEY env var
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

from openai import OpenAI

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BASE_URL  = "https://openrouter.ai/api/v1"
MODEL     = "deepseek/deepseek-v4-flash"

# ─────────────────────────────────────────────────────────────────
# Words to backfill
# ─────────────────────────────────────────────────────────────────

WORDS: list[dict] = [
    # phase_1 — concrete places
    {"word": "temple",     "article": "a",  "phase": 1,
     "hint": "a religious or cultural building for prayer and ceremony; has columns or steps; quiet inside"},
    {"word": "outside",    "article": "",   "phase": 1,
     "hint": "the area or space beyond a building or wall; open air; opposite of inside"},

    # phase_2 — institutions and professions
    {"word": "university", "article": "a",  "phase": 2,
     "hint": "a large school for adults; people study and earn degrees there; has many buildings and subjects"},
    {"word": "colleague",  "article": "a",  "phase": 2,
     "hint": "a person who works at the same place as another person; a co-worker; professional peer"},
    {"word": "lawyer",     "article": "a",  "phase": 2,
     "hint": "a person who knows the law and helps other people with legal problems; speaks in court"},
    {"word": "director",   "article": "a",  "phase": 2,
     "hint": "a person who leads and organises a film, play, or organisation; gives instructions to others"},
    {"word": "waiter",     "article": "a",  "phase": 2,
     "hint": "a person who brings food and drink to people at a table in a restaurant"},
    {"word": "boss",       "article": "a",  "phase": 2,
     "hint": "a person who is in charge at a workplace; gives tasks to other workers"},
]


# ─────────────────────────────────────────────────────────────────
# Prompt
# ─────────────────────────────────────────────────────────────────

PROMPT_TPL = """\
Generate one Ninereeds phase corpus file for the word "{word}".

## Format rules — follow exactly

The file has exactly 4 [user]/[Ninereeds] block pairs separated by blank lines.

Questions (use these in order):
  Q1: What does {noun_phrase} look like?
  Q2: Where can you find {noun_phrase}?
  Q3: What does {noun_phrase} do?
  Q4: What does {noun_phrase} give?

Each [Ninereeds] block:
  - First line: [Ninereeds] immediately followed by a statement (no blank between tag and text)
  - 5 more lines after the first (6 lines total per block)
  - Last line: a summary combining two properties from the block (use "and")
  - One sentence per line. One period per line.
  - Subject of every line is "{word}" or a part of "{word}".
  - No pronouns (no it, its, they, them, he, she, etc.)
  - No negation (no not, never, no, without, etc.)
  - Use "{cap_word}" or "The {word}" to start lines.

## Word context

{hint}

## Example (for word "street")

[user]What does a street look like?
[Ninereeds]A street is a long flat path.
A street is paved with asphalt.
A street is gray and black.
A street has white lines on top.
A street has sidewalks on the sides.
A street is a long flat path and paved with asphalt.

[user]Where can you find a street?
[Ninereeds]A street is in a town.
A street is between buildings.
A street runs through a city.
A street connects one place to another.
A street is in a neighborhood.
A street is in a town and between buildings.

[user]What does a street do?
[Ninereeds]A street carries cars and trucks.
A street guides people to a destination.
A street stays still under wheels.
A street holds up heavy loads.
A street gets hot in the sun.
A street carries cars and trucks and guides people.

[user]What does a street give?
[Ninereeds]A street is for driving.
A street is for walking.
A street is for biking.
A street moves traffic from place to place.
A street leads a traveler to a home.
A street is for driving and walking.

## Output

Return the file content only. No commentary. No markdown fences. No labels."""


# ─────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────

PRONOUN_RE = re.compile(
    r"\b(it|its|they|them|their|he|him|his|she|her|hers|we|our|us|you|your)\b",
    re.IGNORECASE,
)
NEGATION_RE = re.compile(
    r"\b(not|never|no|without|neither|nor|nothing|nobody|nowhere|hardly|barely|scarcely)\b",
    re.IGNORECASE,
)


def validate(word: str, content: str) -> list[str]:
    errors = []
    blocks = [b.strip() for b in content.strip().split("\n\n") if b.strip()]

    if len(blocks) != 4:
        errors.append(f"expected 4 blocks, got {len(blocks)}")
        return errors

    for i, block in enumerate(blocks):
        lines = block.splitlines()
        if not lines[0].startswith("[user]"):
            errors.append(f"block {i+1}: first line not [user]")
        if len(lines) < 2 or not lines[1].startswith("[Ninereeds]"):
            errors.append(f"block {i+1}: second line not [Ninereeds]")
            continue
        ninereeds_lines = lines[1:]
        if len(ninereeds_lines) != 6:
            errors.append(f"block {i+1}: expected 6 [Ninereeds] lines, got {len(ninereeds_lines)}")
        for ln in ninereeds_lines:
            text = re.sub(r"^\[Ninereeds\]", "", ln)
            m = PRONOUN_RE.search(text)
            if m:
                errors.append(f"block {i+1}: pronoun '{m.group()}' in: {text[:60]}")
            m = NEGATION_RE.search(text)
            if m:
                errors.append(f"block {i+1}: negation '{m.group()}' in: {text[:60]}")

    return errors


# ─────────────────────────────────────────────────────────────────
# Generation
# ─────────────────────────────────────────────────────────────────

def load_api_key() -> str:
    for var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        if key := os.environ.get(var):
            return key
    return ""


def generate_one(entry: dict, client: OpenAI, dry_run: bool) -> bool:
    word    = entry["word"]
    article = entry["article"]
    phase   = entry["phase"]
    hint    = entry["hint"]

    out_path = REPO_ROOT / "training_data" / "phases" / f"phase_{phase}" / f"{word}.md"

    if out_path.exists():
        print(f"  SKIP {word} — already exists at {out_path.relative_to(REPO_ROOT)}")
        return True

    if dry_run:
        print(f"  [DRY-RUN] would generate {out_path.relative_to(REPO_ROOT)}")
        return True

    noun_phrase = f"{article} {word}".strip() if article else word
    cap_word = word.capitalize()
    prompt = PROMPT_TPL.format(
        word=word, noun_phrase=noun_phrase, cap_word=cap_word, hint=hint
    )

    for attempt in (1, 2):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
            )
        except Exception as e:
            print(f"  API ERROR (attempt {attempt}) {word}: {e}")
            if attempt == 2:
                return False
            time.sleep(2)
            continue

        content = (resp.choices[0].message.content or "").strip()
        # strip markdown fences if present
        content = re.sub(r"^```[^\n]*\n", "", content)
        content = re.sub(r"\n?```$", "", content.strip())

        errors = validate(word, content)
        if errors:
            print(f"  VALIDATE FAIL (attempt {attempt}) {word}:")
            for e in errors:
                print(f"    {e}")
            if attempt == 2:
                return False
            continue

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content + "\n", encoding="utf-8")
        tokens_in  = resp.usage.prompt_tokens     if resp.usage else "?"
        tokens_out = resp.usage.completion_tokens if resp.usage else "?"
        print(f"  OK {word} → phase_{phase}/{word}.md  ({tokens_in}→{tokens_out})")
        return True

    return False


# ─────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Phase backfill generator")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    api_key = load_api_key()
    if not api_key and not args.dry_run:
        print("ERROR: set OPENROUTER_API_KEY or OPENAI_API_KEY", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key or "dry", base_url=BASE_URL)

    print(f"Generating {len(WORDS)} phase files...")
    ok = failed = 0
    for entry in WORDS:
        if generate_one(entry, client, args.dry_run):
            ok += 1
        else:
            failed += 1

    print(f"\nDone: {ok} written, {failed} failed.")


if __name__ == "__main__":
    main()
