#!/usr/bin/env python3
"""
annotate_stories.py — Create _marked.md annotation pairs for all teaching stories.

For each teaching story file (e.g. dolphin.md), generates a dolphin_marked.md
alongside it with case-role annotations on every sentence in all 4 languages.

Annotation brackets (same as bridge files):
  (NOM)  = subject      *verb* = main verb
  {ACC}  = direct obj   [DAT]  = indirect obj / dative complement
  <GEN>  = genitive / possessive

Preserves the [user]/[Ninereeds] structure. Only the [Ninereeds] answer blocks
are annotated; the [user] question lines are left unchanged.

Model: deepseek/deepseek-v4-flash via OpenRouter
Progress: skips files where _marked.md already exists

Usage:
  python3 meta/scripts/annotate_stories.py [--workers 6] [--batch 50]
  python3 meta/scripts/annotate_stories.py --status
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

STORIES_DIR = ROOT / "training_data" / "01_language" / "teaching_stories"
MODEL       = "deepseek/deepseek-v4-flash"
MAX_TOKENS  = 32768
TEMPERATURE = 0.3

_print_lock = threading.Lock()

ANNOTATION_PROMPT = """\
Annotate this teaching story with grammatical case markers. Output the annotated version \
in exactly the same [user]/[Ninereeds] format as the input.

WHAT TO ANNOTATE:
- Only the [Ninereeds] answer blocks — NOT the [user] question lines.
- Annotate all four language versions (EN, DE, JP, ZH).
- Every sentence gets (NOM) and *verb* markers.
- Add {ACC}, [DAT], <GEN> only where the role is present.

ANNOTATION BRACKETS:
  (NOM) = subject — the one performing the action
  *verb* = the main content verb (not auxiliaries like "is" unless it's the only verb)
  {ACC} = direct object — directly acted upon (ACC in DE, を in JP, pre-verb object in ZH/EN)
  [DAT] = indirect object OR dative-governed prepositional phrase
          — German: nouns after dative prepositions (auf/an/in/bei/mit/von/zu/nach/seit etc. in locative sense), or indirect object
          — Japanese: nouns marked with に (goal/recipient)
          — English/Chinese: mark consistently with the German/Japanese equivalent
  <GEN> = genitive / possessive — "of X" or "X's" constructions, の in Japanese, 的 phrases in Chinese

RULES:
1. (NOM) and *verb* appear in every sentence.
2. Predicate adjectives: (subject) *is* adjective  — no ACC bracket for bare adjectives.
3. Predicate nouns: (subject) *is* {a noun} — use ACC bracket for the predicate NP.
4. Intransitive: (subject) *verb* place/manner — bracket prepositional phrases as [DAT] if dative.
5. Existential: (there) *is* {something} — mark the nominal as ACC.
6. Passive / impersonal: mark the logical subject as (NOM) if expressed.
7. Keep everything OUTSIDE brackets unchanged — do not paraphrase, reorder, or omit any words.
8. Apply the same bracket position consistently across all 4 languages for the same semantic role.

EXAMPLES (for reference):

DE: Das Kind findet einen schattigen Baum.
→   (Das Kind) *findet* {einen schattigen Baum}.

DE: Ein Kind geht auf einem Weg.
→   (Ein Kind) *geht* auf [einem Weg].

DE: Die Sonne ist heiß.
→   (Die Sonne) *ist* heiß.

DE: Der Mann gibt dem Hund den Ball des Jungen.
→   (Der Mann) *gibt* [dem Hund] {den Ball <des Jungen>}.

DE: Das Kind ist ein freundliches Tier.
→   (Das Kind) *ist* {ein freundliches Tier}.

JP: 子供が小道を歩く。
→   (子供が){小道を}*歩く*。

JP: 太陽は熱い。
→   (太陽は)*熱い*。

JP: イルカが近くを泳ぐ。
→   (イルカが){近くを}*泳ぐ*。

EN: A child walks on a path.
→   (A child) *walks* on [a path].

EN: The child finds a shady tree.
→   (The child) *finds* {a shady tree}.

EN: The sun is hot.
→   (The sun) *is* hot.

ZH: 一個孩子走在一條小路上。
→   (一個孩子)*走*在[一條小路上]。

ZH: 海豚游近。
→   (海豚)*游*近。

STORY TO ANNOTATE:
---
{content}
---

Output ONLY the annotated story with the exact same [user]/[Ninereeds] structure. \
No explanation, no markdown fences, no added text."""


def find_all_stories() -> list[Path]:
    return sorted(
        p for p in STORIES_DIR.rglob("*.md")
        if not p.stem.endswith("_marked")
    )


def marked_path(story: Path) -> Path:
    return story.with_stem(story.stem + "_marked")


def verify_output(original: str, annotated: str) -> str | None:
    """Returns None if OK, or an error message."""
    # Must preserve [user] / [Ninereeds] tags
    orig_tags  = re.findall(r"\[user\]|\[Ninereeds\]", original)
    annot_tags = re.findall(r"\[user\]|\[Ninereeds\]", annotated)
    if orig_tags != annot_tags:
        return f"tag mismatch: expected {len(orig_tags)}, got {len(annot_tags)}"

    # Must contain annotation brackets
    if "(" not in annotated or "*" not in annotated:
        return "no annotation brackets found"

    # Rough length sanity: annotated should be longer than original (brackets added)
    if len(annotated) < len(original) * 0.9:
        return f"output suspiciously short ({len(annotated)} vs {len(original)})"

    return None


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
    content = "\n".join(l for l in content.splitlines() if l.strip() != "---").strip()
    return content


def process_story(story: Path, api_key: str) -> tuple[Path, bool, str]:
    out_path = marked_path(story)
    if out_path.exists():
        return (story, True, "skip")

    original = story.read_text("utf-8")
    prompt   = ANNOTATION_PROMPT.replace("{content}", original)

    try:
        result = call_api(prompt, api_key)
    except Exception as e:
        return (story, False, f"API error: {e}")

    err = verify_output(original, result)
    if err:
        return (story, False, f"verify: {err}")

    out_path.write_text(result + "\n", "utf-8")
    return (story, True, "ok")


def cmd_run(args):
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("ERROR: OPENROUTER_API_KEY not set")

    all_stories = find_all_stories()
    pending     = [s for s in all_stories if not marked_path(s).exists()]

    if args.batch:
        pending = pending[:args.batch]

    total = len(all_stories)
    done  = total - len([s for s in all_stories if not marked_path(s).exists()])
    print(f"{total} stories total | {done} already annotated | {len(pending)} to process")

    if not pending:
        print("Nothing to do.")
        return

    ok = fail = skip = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(process_story, s, api_key): s for s in pending}
        for fut in as_completed(futures):
            story, success, msg = fut.result()
            rel = story.relative_to(STORIES_DIR)
            with _print_lock:
                if msg == "skip":
                    skip += 1
                elif success:
                    print(f"  OK    {rel}")
                    ok += 1
                else:
                    print(f"  FAIL  {rel}: {msg}", file=sys.stderr)
                    fail += 1

    print(f"\nDone: {ok} annotated, {skip} already done, {fail} failed")
    if fail:
        sys.exit(1)


def cmd_status(args):
    all_stories = find_all_stories()
    done  = [s for s in all_stories if marked_path(s).exists()]
    pend  = [s for s in all_stories if not marked_path(s).exists()]
    print(f"Total stories   : {len(all_stories)}")
    print(f"Annotated (_marked.md): {len(done)}")
    print(f"Remaining       : {len(pend)}")
    if pend:
        print(f"\nFirst 5 pending:")
        for s in pend[:5]:
            print(f"  {s.relative_to(STORIES_DIR)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--batch",   type=int, default=0,
                        help="Process at most N stories then stop (0 = all)")
    parser.add_argument("--status",  action="store_true")
    args = parser.parse_args()

    if args.status:
        cmd_status(args)
    else:
        cmd_run(args)


if __name__ == "__main__":
    main()
