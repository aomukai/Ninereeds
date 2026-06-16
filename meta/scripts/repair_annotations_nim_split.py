#!/usr/bin/env python3
"""
repair_annotations_nim_split.py — Repair _marked.md files by splitting into 4 language sections.

For files that failed the main NIM pass (typically because the correct repaired output is shorter
than 80% of the bloated original), this script processes each language section independently.
Each [user]/[Ninereeds] pair is sent as a separate API call, then the four sections are merged.

This also works around cases where the original annotator left reasoning text embedded in the
file (common in JP/ZH blocks), which inflates file size and confuses whole-file repair passes.

Verification is lenient (tag counts + annotation presence, no length check), because many of
these files have bloated originals where the correct output is legitimately shorter.

Done file: tmp/repair_nim_split_done.txt
Skips files already in: tmp/repair_nim_split_done.txt

Input sources (in priority order):
  --files f1 f2 ...     explicit paths
  --from-list FILE      read paths from FILE (one per line, relative to STORIES_DIR or absolute)
  (default)             read from tmp/nim_failures.txt

Usage:
  NVIDIA_API_KEY=nvapi-xxx python3 meta/scripts/repair_annotations_nim_split.py
  NVIDIA_API_KEY=nvapi-xxx python3 meta/scripts/repair_annotations_nim_split.py --workers 4
  NVIDIA_API_KEY=nvapi-xxx python3 meta/scripts/repair_annotations_nim_split.py --files training_data/.../birdhouse_marked.md
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT        = Path(__file__).resolve().parent.parent.parent
STORIES_DIR = ROOT / "training_data" / "01_language" / "teaching_stories"
DONE_FILE   = ROOT / "tmp" / "repair_nim_split_done.txt"
DEFAULT_LIST = ROOT / "tmp" / "nim_failures.txt"

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
NIM_MODEL    = "deepseek-ai/deepseek-v4-pro"
MAX_TOKENS   = 16384
TEMPERATURE  = 0.2

_print_lock = threading.Lock()

# Per-section repair prompt — single language, lenient length check omitted.
# Uses .replace() so annotation brackets like (NOM), {ACC}, [DAT], <GEN> in the
# prompt text are never treated as Python format tokens.
SECTION_PROMPT = """\
You are reviewing a case-role annotated teaching story section in {language}. \
The [Ninereeds] block has annotation errors. Fix every error and output a fully corrected version.

ANNOTATION RULES (apply to {language}):
1. EVERY sentence in the [Ninereeds] block must have (NOM) and *verb*.
   - (NOM) wraps the full subject NP including articles/determiners.
   - *verb* wraps the SINGLE main content verb only — no auxiliaries, negation words, or participles.
2. [user] lines must NOT be annotated — leave them as plain text.
3. Bracket full constituents:
   - (NOM) wraps entire subject NP.
   - {ACC} wraps entire direct-object NP.
   - [DAT] wraps entire dative NP or PP INCLUDING the preposition.
   - <GEN> wraps entire possessive modifier phrase INCLUDING の/的/des/of.
4. Do NOT force-add optional brackets where the role is not present.
5. Adverbs, time expressions, topic markers are NOT subjects — do NOT wrap in (NOM).
   Bad: (Later,) (Dann) (Später) (今日は) — remove these (NOM) brackets.
6. Negation stays OUTSIDE *verb*: "(Er) *gab* nicht auf" — separable: *gab … auf*
7. ZH 把-constructions: (subject) *verb* {把 + NP}
8. Empty ( ) brackets are errors — always put the subject inside.
9. Do NOT add or remove [user]/[Ninereeds] tags. Do NOT paraphrase or alter text.
10. IMPORTANT: Remove any reasoning, internal commentary, or meta-text that appears in the \
[Ninereeds] block — output ONLY the annotated story sentences.

ANNOTATED {language} SECTION TO REPAIR:
---
{content}
---

Output ONLY the corrected [user]/[Ninereeds] section with no explanation, no markdown fences, \
no added text. Preserve the exact [user]/[Ninereeds] structure."""


def detect_language(section: str) -> str:
    lines = section.splitlines()
    user_text = ""
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[user]" and i + 1 < len(lines):
            user_text = lines[i + 1]
            break
        if stripped.startswith("[user]") and len(stripped) > 6:
            user_text = stripped[6:].strip()
            break
    if any('぀' <= c <= 'ヿ' for c in user_text):
        return "Japanese"
    if any('一' <= c <= '鿿' for c in user_text):
        return "Chinese"
    lower = user_text.lower()
    de_markers = ['ä', 'ö', 'ü', 'ß']
    de_words   = ['ich ', 'möchte', 'über', ' ein ', ' eine ', ' der ', ' die ', ' das ',
                  'lernen', 'etwas', 'ist ', 'sind ', 'was ']
    if any(m in lower for m in de_markers) or any(w in lower for w in de_words):
        return "German"
    return "English"


def split_sections(content: str) -> list[str]:
    # Split on one or more newlines immediately before a [user] tag.
    # Handles both single-newline (\n[user]) and double-newline (\n\n[user]) boundaries.
    parts = re.split(r'\n+(?=\[user\])', content.strip())
    return [p.strip() for p in parts if p.strip()]


def call_api(prompt: str, api_key: str, retries: int = 5) -> str:
    from openai import OpenAI
    client = OpenAI(base_url=NIM_BASE_URL, api_key=api_key)
    delay = 30
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=NIM_MODEL,
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                messages=[{"role": "user", "content": prompt}],
                extra_body={"chat_template_kwargs": {"thinking": False}},
            )
            content = resp.choices[0].message.content or ""
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            if content.startswith("```"):
                content = "\n".join(l for l in content.splitlines()
                                    if not l.startswith("```")).strip()
            content = "\n".join(l for l in content.splitlines()
                                if l.strip() != "---").strip()
            return content
        except Exception as e:
            err_str = str(e)
            is_rate_limit = "429" in err_str or "rate" in err_str.lower()
            if attempt < retries - 1:
                wait = delay * (2 ** attempt) if is_rate_limit else delay
                with _print_lock:
                    print(f"  [retry {attempt+1}/{retries}] {err_str[:80]} — waiting {wait}s",
                          file=sys.stderr)
                time.sleep(wait)
            else:
                raise


def verify_section(section_idx: int, original: str, repaired: str) -> str | None:
    # Count [user] and [Ninereeds] tags — must match original exactly.
    orig_user = original.count("[user]")
    orig_nr   = original.count("[Ninereeds]")
    rep_user  = repaired.count("[user]")
    rep_nr    = repaired.count("[Ninereeds]")
    if rep_user != orig_user or rep_nr != orig_nr:
        return (f"tag count mismatch: expected {orig_user}u/{orig_nr}nr, "
                f"got {rep_user}u/{rep_nr}nr")
    # Check annotations present.
    if "(" not in repaired or "*" not in repaired:
        return "annotation brackets missing"
    # Check [Ninereeds] block has real content.
    nr_idx = repaired.find("[Ninereeds]")
    if nr_idx == -1:
        return "no [Ninereeds] tag found"
    nr_content = repaired[nr_idx + len("[Ninereeds]"):].strip()
    if len(nr_content) < 30:
        return f"[Ninereeds] block too short ({len(nr_content)} chars)"
    return None
    # NOTE: no length-vs-original check here. Many of these files have reasoning text
    # embedded in the original, so the correctly-repaired output is legitimately shorter.


def verify_merged(original: str, merged: str) -> str | None:
    orig_tags   = re.findall(r"\[user\]|\[Ninereeds\]", original)
    merged_tags = re.findall(r"\[user\]|\[Ninereeds\]", merged)
    if orig_tags != merged_tags:
        return (f"merged tag mismatch: expected {len(orig_tags)} "
                f"({orig_tags.count('[user]')}u/{orig_tags.count('[Ninereeds]')}nr), "
                f"got {len(merged_tags)}")
    if "(" not in merged or "*" not in merged:
        return "merged file missing annotation brackets"
    return None


def repair_file_split(path: Path, api_key: str) -> tuple[Path, bool, str]:
    original = path.read_text("utf-8")
    sections = split_sections(original)

    if len(sections) < 4:
        return path, False, f"too few sections: expected at least 4, got {len(sections)}"

    repaired_sections: list[str] = []
    for i, section in enumerate(sections):
        lang = detect_language(section)
        prompt = (SECTION_PROMPT
                  .replace("{language}", lang)
                  .replace("{content}", section))
        try:
            result = call_api(prompt, api_key)
        except Exception as e:
            return path, False, f"API error section {i+1} ({lang}): {e}"

        err = verify_section(i, section, result)
        if err:
            return path, False, f"section {i+1} ({lang}): {err}"

        repaired_sections.append(result)
        if i < len(sections) - 1:
            time.sleep(5)  # pace calls to avoid NIM free-tier rate limits

    merged = "\n\n".join(repaired_sections)
    err = verify_merged(original, merged)
    if err:
        return path, False, f"merged verify: {err}"

    path.write_text(merged + "\n", "utf-8")
    return path, True, "ok"


def path_to_slug(p: Path) -> str:
    return str(p.relative_to(STORIES_DIR))


def load_done() -> set[str]:
    if DONE_FILE.exists():
        return set(DONE_FILE.read_text("utf-8").splitlines())
    return set()


def mark_done(slug: str) -> None:
    with open(DONE_FILE, "a", encoding="utf-8") as f:
        f.write(slug + "\n")


def resolve_path(p_str: str) -> Path:
    p = Path(p_str)
    if p.is_absolute():
        return p
    # Try relative to repo root first, then STORIES_DIR.
    if (ROOT / p).exists():
        return ROOT / p
    if (STORIES_DIR / p).exists():
        return STORIES_DIR / p
    return p  # let the caller handle missing


def load_file_list(list_path: Path) -> list[Path]:
    if not list_path.exists():
        sys.exit(f"ERROR: file list not found: {list_path}")
    paths = []
    for line in list_path.read_text("utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        p = resolve_path(line)
        if p.exists():
            paths.append(p)
        else:
            print(f"  WARN: not found: {line}", file=sys.stderr)
    return paths


def cmd_run(args, api_key: str) -> None:
    if args.files:
        targets = [resolve_path(f) for f in args.files]
    elif args.from_list:
        targets = load_file_list(Path(args.from_list))
    else:
        targets = load_file_list(DEFAULT_LIST)

    if not targets:
        print("No target files. Run after NIM pass completes to generate nim_failures.txt.")
        return

    done_slugs = load_done()
    pending    = [p for p in targets if path_to_slug(p) not in done_slugs]
    skipped    = len(targets) - len(pending)

    print(f"Model: {NIM_MODEL} (split mode) | {len(targets)} files | "
          f"{skipped} already done | {len(pending)} to repair")
    if not pending:
        print("Nothing to do.")
        return

    ok = fail = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures    = {pool.submit(repair_file_split, p, api_key): p for p in pending}
        done_count = skipped
        for fut in as_completed(futures):
            path, success, msg = fut.result()
            done_count += 1
            slug = path_to_slug(path)
            rel  = path.relative_to(STORIES_DIR)
            with _print_lock:
                if success:
                    print(f"  [{done_count:4d}/{len(targets)}] OK      {rel}")
                    ok += 1
                else:
                    print(f"  [{done_count:4d}/{len(targets)}] FAIL    {rel}: {msg}",
                          file=sys.stderr)
                    fail += 1
            if success:
                mark_done(slug)

    print(f"\nDone: {ok} repaired, {skipped} skipped, {fail} failed")
    if fail:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repair _marked.md files by splitting into 4 language sections."
    )
    parser.add_argument("--files", nargs="+",
                        help="Explicit _marked.md paths to repair")
    parser.add_argument("--from-list", metavar="FILE",
                        help="File containing paths to repair (default: tmp/nim_failures.txt)")
    parser.add_argument("--workers", type=int, default=4,
                        help="Parallel workers (default: 4)")
    args = parser.parse_args()

    api_key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("ERROR: NVIDIA_API_KEY not set")

    cmd_run(args, api_key)


if __name__ == "__main__":
    main()
