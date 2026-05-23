#!/usr/bin/env python3
"""
Generate arithmetic drill files for teacher_student_drill intervention (run_7).

Produces [user]/[Ninereeds] format files that directly train the probe response
pattern: "What is X plus X?" → "X plus X is Y."

Existing reasoning files use "Teach me about..." / multi-modal format which does
not match probe output expectations. These drills bridge that gap.

Output: training_data/reasoning/drill_*.md
"""

import os
import pathlib
import sys
import time

from openai import OpenAI

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT_DIR = ROOT / "training_data" / "reasoning"

BASE_URL = "https://openrouter.ai/api/v1"
MODEL    = "deepseek/deepseek-v4-flash"

# ── Drill specs ───────────────────────────────────────────────────────────────
# Each spec: (filename_stem, intro_comment, list of (question, correct_answer))
# Answers are hardcoded — DeepSeek is asked to phrase them, not calculate them.

DRILL_SPECS = [
    ("drill_add_direct_1", "Single-digit addition — direct probe format", [
        ("What is one plus one?",   "One plus one is two."),
        ("What is two plus one?",   "Two plus one is three."),
        ("What is two plus two?",   "Two plus two is four."),
        ("What is three plus one?", "Three plus one is four."),
    ]),
    ("drill_add_direct_2", "Single-digit addition — fours and fives", [
        ("What is three plus two?", "Three plus two is five."),
        ("What is four plus one?",  "Four plus one is five."),
        ("What is four plus two?",  "Four plus two is six."),
        ("What is three plus three?","Three plus three is six."),
    ]),
    ("drill_add_direct_3", "Single-digit addition — sixes and sevens", [
        ("What is four plus three?", "Four plus three is seven."),
        ("What is five plus two?",   "Five plus two is seven."),
        ("What is five plus three?", "Five plus three is eight."),
        ("What is four plus four?",  "Four plus four is eight."),
    ]),
    ("drill_add_direct_4", "Single-digit addition — eights and nines", [
        ("What is five plus four?",  "Five plus four is nine."),
        ("What is six plus three?",  "Six plus three is nine."),
        ("What is five plus five?",  "Five plus five is ten."),
        ("What is six plus four?",   "Six plus four is ten."),
    ]),
    ("drill_zero_direct_1", "Zero — direct probe format", [
        ("What is zero?",            "Zero is a number."),
        ("What is zero plus one?",   "Zero plus one is one."),
        ("What is zero plus three?", "Zero plus three is three."),
        ("What is zero plus zero?",  "Zero plus zero is zero."),
    ]),
    ("drill_zero_direct_2", "Zero identity and subtraction", [
        ("What is two plus zero?",   "Two plus zero is two."),
        ("What is five plus zero?",  "Five plus zero is five."),
        ("What is three minus zero?","Three minus zero is three."),
        ("What is four minus four?", "Four minus four is zero."),
    ]),
    ("drill_sub_direct_1", "Single-digit subtraction — direct probe format", [
        ("What is two minus one?",   "Two minus one is one."),
        ("What is three minus one?", "Three minus one is two."),
        ("What is four minus two?",  "Four minus two is two."),
        ("What is five minus three?","Five minus three is two."),
    ]),
    ("drill_sub_direct_2", "Single-digit subtraction — larger differences", [
        ("What is five minus two?",  "Five minus two is three."),
        ("What is six minus three?", "Six minus three is three."),
        ("What is seven minus four?","Seven minus four is three."),
        ("What is eight minus five?","Eight minus five is three."),
    ]),
    ("drill_numbers_1", "Number identity — what is N?", [
        ("What is one?",   "One is a number."),
        ("What is two?",   "Two is a number."),
        ("What is three?", "Three is a number."),
        ("What is four?",  "Four is a number."),
    ]),
    ("drill_numbers_2", "Number identity — five through ten", [
        ("What is five?",  "Five is a number."),
        ("What is six?",   "Six is a number."),
        ("What is seven?", "Seven is a number."),
        ("What is eight?", "Eight is a number."),
    ]),
    ("drill_equals_1", "Equals and result — reinforcing the 'equals' frame", [
        ("What does two plus two equal?",   "Two plus two equals four."),
        ("What does three plus two equal?",  "Three plus two equals five."),
        ("What does four plus three equal?", "Four plus three equals seven."),
        ("What does five plus five equal?",  "Five plus five equals ten."),
    ]),
    ("drill_add_review", "Addition review — mixed facts including two plus two", [
        ("What is two plus two?",    "Two plus two is four."),
        ("What is three plus three?","Three plus three is six."),
        ("What is four plus four?",  "Four plus four is eight."),
        ("What is five plus five?",  "Five plus five equals ten."),
    ]),
]

# ── Prompt template ───────────────────────────────────────────────────────────

SYSTEM = """\
You write training data for a small language model called Ninereeds.
The format is strict [user]/[Ninereeds] dialogue.
You will be given a list of (question, correct answer) pairs.
For each pair, write one [user]/[Ninereeds] block.

Format rules:
- [user] line: the exact question provided.
- [Ninereeds] first line (on same line as tag): the exact answer provided.
- 2 to 4 additional lines: rephrase the same fact differently.
  Each line is one sentence. Each sentence ends with a period.
  No pronouns (no it, its, they, them, he, she, we, you, I).
  No negation in the body lines.
  All phrasings must state the same correct answer.
- Blank line between blocks.

The answer provided is ALWAYS correct. Do not change the answer or calculate anything yourself.

Example input pair:
  question: "What is two plus two?"
  answer: "Two plus two is four."

Example output:
[user]What is two plus two?
[Ninereeds]Two plus two is four.
Two and two make four.
Four is the sum of two and two.
Adding two to two gives four.

Only output the blocks. No headers, no explanations, no markdown.
"""

def make_user_prompt(pairs):
    lines = ["Generate one [user]/[Ninereeds] block for each of the following pairs:\n"]
    for i, (q, a) in enumerate(pairs, 1):
        lines.append(f"{i}. question: \"{q}\"")
        lines.append(f"   answer: \"{a}\"")
    return "\n".join(lines)

# ── Validation ────────────────────────────────────────────────────────────────

def validate(text, pairs):
    """Return list of error strings, empty if OK."""
    errors = []
    for q, a in pairs:
        q_lower = q.lower().rstrip("?")
        # Check question appears
        if f"[user]{q}" not in text and f"[user]{q.lower()}" not in text:
            errors.append(f"Missing [user] block for: {q}")
        # Check answer first word sequence appears
        key = a.split(".")[0].lower()
        if key not in text.lower():
            errors.append(f"Answer not found: {a}")
    # Check no pronoun leak in Ninereeds lines
    for line in text.splitlines():
        if line.startswith("[Ninereeds]") or (not line.startswith("[user]") and line.strip()):
            low = line.lower()
            for p in [" it ", " it.", " its ", " they ", " them ", " he ", " she ", " we ", " you ", " i "]:
                if p in f" {low} ":
                    errors.append(f"Pronoun in Ninereeds line: {line.strip()}")
                    break
    return errors

# ── Main ──────────────────────────────────────────────────────────────────────

def load_api_key():
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    auth = pathlib.Path.home() / ".local/share/opencode/auth.json"
    if auth.exists():
        import json
        data = json.loads(auth.read_text())
        return data.get("openrouter", {}).get("key") or data.get(".openrouter.key")
    return None

def generate_file(spec, client, dry_run=False):
    stem, comment, pairs = spec
    out_path = OUT_DIR / f"{stem}.md"

    if out_path.exists():
        print(f"  SKIP {stem}.md (already exists)")
        return True

    print(f"  GEN  {stem}.md ({len(pairs)} pairs) ...", end=" ", flush=True)

    if dry_run:
        print("DRY RUN")
        return True

    user_prompt = make_user_prompt(pairs)
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=1024,
            temperature=0.3,
        )
        text = resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"ERROR: {e}")
        return False

    errors = validate(text, pairs)
    if errors:
        print(f"VALIDATION FAILED:")
        for e in errors:
            print(f"    {e}")
        # Save to tmp for inspection
        tmp = ROOT / "tmp" / f"{stem}_failed.md"
        tmp.write_text(text)
        print(f"    Saved failed output to {tmp}")
        return False

    header = f"# {comment}\n\n"
    out_path.write_text(header + text + "\n")
    print(f"OK ({len(text.splitlines())} lines)")
    return True

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()

    # Load .env if present
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

    api_key = load_api_key()
    if not api_key:
        print("ERROR: No API key found. Set OPENROUTER_API_KEY in .env or environment.")
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    print(f"Generating {len(DRILL_SPECS)} arithmetic drill files → {OUT_DIR}")
    print(f"Model: {MODEL}  |  Workers: {args.workers}  |  Dry-run: {args.dry_run}")
    print()

    import concurrent.futures
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(generate_file, spec, client, args.dry_run): spec[0]
                for spec in DRILL_SPECS}
        for fut in concurrent.futures.as_completed(futs):
            results.append((futs[fut], fut.result()))

    ok  = sum(1 for _, r in results if r)
    bad = sum(1 for _, r in results if not r)
    print(f"\nDone: {ok} OK, {bad} failed")
    if bad:
        print("Re-run to retry failed files (existing files are skipped).")
        sys.exit(1)

if __name__ == "__main__":
    main()
