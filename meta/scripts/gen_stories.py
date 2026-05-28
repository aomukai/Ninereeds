#!/usr/bin/env python3
"""
gen_stories.py — generate grounded stories (EN/DE/JP/ZH) for the Ninereeds corpus.

Reads world_bible.md and storylist.txt, sends one story spec per DeepSeek call,
writes story_NN_LANG.md for each entry.

Usage:
  python3 meta/scripts/gen_stories.py gen [--lang EN,DE,JP,ZH] [--workers 6] [--only 01,05] [--dry-run]
  python3 meta/scripts/gen_stories.py report [--lang EN,DE,JP,ZH]

Auth: OPENROUTER_API_KEY env var
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT   = Path(__file__).resolve().parent.parent.parent
STORIES_DIR  = REPO_ROOT / "training_data" / "grounded_stories"
CORPUS_ADMIN = REPO_ROOT / "training" / "corpus_admin" / "grounded_stories"
WORLD_BIBLE  = CORPUS_ADMIN / "world_bible.md"
STORY_LIST   = CORPUS_ADMIN / "storylist.txt"
BASE_URL    = "https://openrouter.ai/api/v1"
MODEL       = "deepseek/deepseek-chat"
MAX_TOKENS  = 1200

CHAR_MAP = {"E": "Emma", "T": "Taro", "G": "Gran", "B": "Biscuit", "L": "Bello"}

# Cast names per language — same characters, language-appropriate rendering
CAST: dict[str, dict[str, str]] = {
    "EN": {"Emma": "Emma",     "Taro": "Taro",   "Gran": "Gran",       "Biscuit": "Biscuit",   "Bello": "Bello"},
    "DE": {"Emma": "Emma",     "Taro": "Taro",   "Gran": "Oma",        "Biscuit": "Keks",        "Bello": "Bello"},
    "JP": {"Emma": "エマ",      "Taro": "太郎",   "Gran": "おばあさん",  "Biscuit": "ビスケット",  "Bello": "ベロ"},
    "ZH": {"Emma": "艾玛",      "Taro": "太郎",   "Gran": "奶奶",       "Biscuit": "饼干",        "Bello": "贝洛"},
}

# Language-specific writing instructions
LANG_INSTRUCTIONS: dict[str, str] = {
    "EN": (
        "Write in English. Beatrix Potter prose, grade 1–2 reading level. "
        "Natural British/universal English — no textbook constructions."
    ),
    "DE": (
        "Write in German. Natural children's prose — the register of Astrid Lindgren translated "
        "into German, or early-reader German picture books. Grade 1–2 reading level. "
        "Short sentences. No textbook constructions (not: 'Das ist ein Apfel'). "
        "Characters: Emma, Taro, Oma (grandmother), Keks (dog), Bello (second dog, appears from story 48)."
    ),
    "JP": (
        "Write in Japanese. Natural children's prose — the register of a Ghibli picture book or "
        "Japanese early reader (e.g. はじめてのおつかい level). Grade 1–2. "
        "Use plain/casual forms (だ・の・よ・ね), not formal/keigo. "
        "Short sentences. No textbook constructions (not: '私はエマです'). "
        "Characters: エマ、太郎、おばあさん、ビスケット（犬）、ベロ（二番目の犬、物語48から登場）。"
    ),
    "ZH": (
        "Write in Simplified Chinese (Mandarin). Natural children's prose — the register of "
        "a Chinese picture book for ages 6–8. Grade 1–2. Short sentences. "
        "No textbook constructions (not: '我是艾玛'). "
        "Characters: 艾玛、太郎、奶奶、饼干（狗）、贝洛（第二只狗，从故事48开始出现）。"
    ),
}

# Character names to check for in validation, per language
CHAR_NAMES: dict[str, list[str]] = {
    "EN": ["Emma", "Taro", "Gran", "Biscuit", "Bello"],
    "DE": ["Emma", "Taro", "Oma", "Keks", "Bello"],
    "JP": ["エマ", "太郎", "おばあさん", "ビスケット", "ベロ"],
    "ZH": ["艾玛", "太郎", "奶奶", "饼干", "贝洛"],
}

_lock = threading.Lock()


def log(msg: str) -> None:
    with _lock:
        print(msg, flush=True)


def load_api_key() -> str:
    for var in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        if key := os.environ.get(var):
            return key
    sys.exit("Set OPENROUTER_API_KEY")


# ─────────────────────────────────────────────────────────────────
# Parse storylist.txt
# ─────────────────────────────────────────────────────────────────

def parse_storylist(path: Path) -> list[dict]:
    stories = []
    current: dict = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            if current.get("id"):
                stories.append(current)
                current = {}
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip().upper()
            val = val.strip()
            if key == "STORY":
                if current.get("id"):
                    stories.append(current)
                current = {"id": val.zfill(2)}
            elif key == "CLUSTER":
                current["cluster"] = val
            elif key == "LOCATION":
                current["location"] = val
            elif key == "SEASON":
                current["season"] = val
            elif key == "CHARACTERS":
                codes = [c.strip() for c in val.split()]
                current["characters"] = [CHAR_MAP.get(c, c) for c in codes]
            elif key == "KEY WORDS":
                current["keywords"] = val
            elif key == "SEED":
                current["seed"] = val
            elif key == "ARITHMETIC":
                current["arithmetic"] = val
            elif key == "ANSWER":
                current["answer"] = val
            elif key == "STATES":
                current["states"] = val
            elif key == "COUNTS":
                current["counts"] = val
            elif key == "PARAPHRASE":
                current["paraphrase"] = val
            elif key == "NOTES":
                current["notes"] = val
            elif key == "SPATIAL_CONCEPT":
                current["spatial_concept"] = val
            elif key == "TEMPORAL_RELATION":
                current["temporal_relation"] = val
            elif key == "CAUSE_EFFECT":
                current["cause_effect"] = val
            elif key == "OBSERVATION_STATE":
                current["observation_state"] = val
    if current.get("id"):
        stories.append(current)
    return stories


# ─────────────────────────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────────────────────────

def build_prompt(bible: str, story: dict, lang: str) -> str:
    cast = CAST[lang]
    chars_in_story = [cast.get(c, c) for c in story["characters"]]
    chars_str = ", ".join(chars_in_story)
    lang_instr = LANG_INSTRUCTIONS[lang]

    # Concept constraints block (spatial, temporal, causal, observational)
    concept_lines = []
    for field, label in [
        ("spatial_concept",   "SPATIAL CONCEPT TO GROUND"),
        ("temporal_relation", "TEMPORAL RELATION TO GROUND"),
        ("cause_effect",      "CAUSE-EFFECT CHAIN"),
        ("observation_state", "OBSERVATION-DEPENDENT STATE"),
    ]:
        if story.get(field):
            concept_lines.append(f"- {label}: {story[field]}")
    concept_block = ("\nCONCEPT CONSTRAINTS (weave in naturally — do not state directly):\n"
                     + "\n".join(concept_lines) + "\n") if concept_lines else ""

    # Arithmetic constraints block
    arithmetic_block = ""
    if story.get("arithmetic"):
        answer    = story.get("answer", "")
        states    = story.get("states", "")
        counts    = story.get("counts", "")
        paraphrase = story.get("paraphrase", "")
        notes     = story.get("notes", "")
        arithmetic_block = f"""
ARITHMETIC CONSTRAINTS (follow exactly — do not invent or change numbers):
- Arithmetic fact: {story['arithmetic']}
- Correct answer (hardcoded — use this word exactly in {lang}): {answer}
- Who states the math aloud: {states}
- Who counts aloud: {counts}
- Paraphrase variant to include: {paraphrase}
{f'- Notes: {notes}' if notes else ''}

The arithmetic answer must be correct. Do not change the numbers or the answer word.
"""

    notes_line = f"\nAUTHOR NOTE: {story['notes']}\n" if (story.get("notes") and not story.get("arithmetic")) else ""

    return f"""{bible}

---

IMPORTANT: This is not a translation. There is no source language.
Each language version of this story is written independently, as if by a fluent native author
who was given a scene description and wrote it fresh. The scene description (SEED below)
tells you WHAT happens. You decide HOW to say it in {lang}.

{lang_instr}

Write story {story['id']} now. Output only the story — no title, no heading, no commentary.

CLUSTER: {story['cluster']}
LOCATION: {story['location']}
SEASON: {story['season']}
CHARACTERS IN THIS STORY: {chars_str}
KEY WORDS TO COVER (use naturally, not forced): {story['keywords']}
SCENE SEED: {story['seed']}
{concept_block}{arithmetic_block}{notes_line}
Requirements:
- 150–220 words. Stop when the scene is complete. Do not pad or summarise.
- Show through action and sensation, not definition.
- Pronouns are fine when the referent is clear from the previous sentence.
- Dialogue must be brief and natural — one or two lines at most.
- No moral, no tidy ending, no character announcing what they have learned.
"""


# ─────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────

EN_TEXTBOOK_PATTERNS = [
    r"(?i)this is an? \w+",
    r"(?i)^\s*I am \w+",
    r"(?i)and they (all )?(went home|were happy|had learned)",
    r"(?i)that day[,\s]+\w+ learned",
    r"(?i)\bthe end\b",
]

def validate(text: str, lang: str) -> list[str]:
    issues = []
    # CJK languages have no spaces — use character count instead of word count
    if lang in ("JP", "ZH"):
        chars = len(text.replace("\n", "").replace(" ", ""))
        if chars < 100:
            issues.append(f"too short ({chars} chars)")
        if chars > 800:
            issues.append(f"too long ({chars} chars)")
    else:
        words = len(text.split())
        if words < 60:
            issues.append(f"too short ({words} words)")
        if words > 350:
            issues.append(f"too long ({words} words)")
    if lang == "EN":
        for pat in EN_TEXTBOOK_PATTERNS:
            if re.search(pat, text):
                issues.append(f"textbook pattern: {pat}")
    if not any(name in text for name in CHAR_NAMES[lang]):
        issues.append("no character names found")
    return issues


# ─────────────────────────────────────────────────────────────────
# Generation
# ─────────────────────────────────────────────────────────────────

def generate_story(
    client: OpenAI,
    bible: str,
    story: dict,
    lang: str,
    dry_run: bool,
) -> tuple[str, str, bool, str]:
    """Returns (story_id, lang, success, message)."""
    sid = story["id"]
    out_path = STORIES_DIR / f"story_{sid}_{lang}.md"

    if out_path.exists():
        return sid, lang, True, "already exists"

    if dry_run:
        log(f"  [{sid}/{lang}] DRY RUN — would generate: {out_path.name}")
        return sid, lang, True, "dry run"

    prompt = build_prompt(bible, story, lang)

    for attempt in (1, 2):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS,
                temperature=0.8,
            )
            text = resp.choices[0].message.content.strip()
        except Exception as e:
            if attempt == 2:
                return sid, lang, False, f"API error: {e}"
            log(f"  [{sid}/{lang}] attempt {attempt} failed: {e} — retrying")
            continue

        issues = validate(text, lang)
        if issues and attempt == 1:
            log(f"  [{sid}/{lang}] validation issues on attempt 1: {issues} — retrying")
            continue
        if issues and attempt == 2:
            log(f"  [{sid}/{lang}] validation issues on attempt 2 (saving anyway): {issues}")

        out_path.write_text(text + "\n", encoding="utf-8")
        word_count = len(text.split())
        return sid, lang, True, f"ok ({word_count}w)"

    return sid, lang, False, "failed after 2 attempts"


# ─────────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────────

def cmd_gen(args: argparse.Namespace) -> None:
    langs = [l.strip().upper() for l in args.lang.split(",")]
    stories = parse_storylist(STORY_LIST)
    if args.only:
        only = {s.zfill(2) for s in args.only.split(",")}
        stories = [s for s in stories if s["id"] in only]

    jobs = [
        (s, lang)
        for lang in langs
        for s in stories
        if not (STORIES_DIR / f"story_{s['id']}_{lang}.md").exists()
    ]

    if not jobs:
        print("All stories already generated.")
        return

    total = len(langs) * len(stories)
    print(f"Jobs to run: {len(jobs)}/{total}  (langs: {', '.join(langs)})")
    bible = WORLD_BIBLE.read_text(encoding="utf-8")
    client = OpenAI(api_key=load_api_key(), base_url=BASE_URL)

    done = skipped = failed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(generate_story, client, bible, s, lang, args.dry_run): (s, lang)
            for s, lang in jobs
        }
        for fut in as_completed(futures):
            sid, lang, ok, msg = fut.result()
            if ok:
                if "already" in msg or "dry run" in msg:
                    skipped += 1
                else:
                    done += 1
            else:
                failed += 1
            status = "ok" if ok else "FAIL"
            log(f"  [{sid}/{lang}] {status} — {msg}")

    print(f"\nDone: {done}  skipped: {skipped}  failed: {failed}")


def cmd_report(args: argparse.Namespace) -> None:
    langs = [l.strip().upper() for l in args.lang.split(",")]
    stories = parse_storylist(STORY_LIST)

    for lang in langs:
        done, missing = [], []
        for s in stories:
            p = STORIES_DIR / f"story_{s['id']}_{lang}.md"
            if p.exists():
                words = len(p.read_text(encoding="utf-8").split())
                done.append((s["id"], s["cluster"], words))
            else:
                missing.append((s["id"], s["cluster"]))
        print(f"\n[{lang}] Generated: {len(done)}/{len(stories)}")
        for sid, cluster, words in done:
            print(f"  [{sid}] {cluster} ({words}w)")
        if missing:
            print(f"  Missing ({len(missing)}):")
            for sid, cluster in missing:
                print(f"  [{sid}] {cluster}")


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate grounded stories for Ninereeds")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_gen = sub.add_parser("gen", help="Generate stories")
    p_gen.add_argument("--lang", type=str, default="EN",
                       help="Comma-separated languages to generate: EN,DE,JP,ZH (default: EN)")
    p_gen.add_argument("--workers", type=int, default=6)
    p_gen.add_argument("--dry-run", action="store_true")
    p_gen.add_argument("--only", type=str, default=None,
                       help="Comma-separated story IDs, e.g. 01,05")

    p_rep = sub.add_parser("report", help="Show generation status")
    p_rep.add_argument("--lang", type=str, default="EN,DE,JP,ZH")

    args = parser.parse_args()
    if args.cmd == "gen":
        cmd_gen(args)
    elif args.cmd == "report":
        cmd_report(args)


if __name__ == "__main__":
    main()
