#!/usr/bin/env python3
"""
repair_annotations.py — Send _marked.md files back to DeepSeek for annotation repair.

DeepSeek reads the already-annotated file, finds errors, and outputs a corrected version.
Overwrites the _marked.md file in place.

Sources (in priority order):
  --from-audit training_data/audit.md   files listed as ISSUES in audit report (default)
  --all                                  all 5006 _marked.md files
  --tier 1                               only tier_N files
  --files a.md b.md                      explicit list

Usage:
  python3 meta/scripts/repair_annotations.py
  python3 meta/scripts/repair_annotations.py --from-audit training_data/audit.md
  python3 meta/scripts/repair_annotations.py --all --workers 6
  python3 meta/scripts/repair_annotations.py --tier 1 --workers 6
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
TEMPERATURE = 0.2

_print_lock = threading.Lock()

REPAIR_PROMPT = """\
You are reviewing an annotated teaching story. The story appears in 4 languages (EN, DE, JP, ZH). \
The [Ninereeds] answer blocks have case-role bracket annotations applied to them. \
Your task: find every annotation error and output a fully corrected version.

ANNOTATION RULES (apply to ALL four languages):
1. EVERY sentence in a [Ninereeds] block must have (NOM) and *verb*.
   - (NOM) wraps the subject — the noun phrase performing the action.
   - *verb* wraps the single main content verb only — no auxiliaries, no negation words, no participles.
   - For adjective predicates (JP: *大きい*, ZH: *很大*) — add the copula and mark it: (subject) *ist* adjective.
2. [user] lines must NOT be annotated — leave them exactly as plain text.
3. Each bracket wraps its full constituent:
   - (NOM) wraps the entire subject NP including articles/determiners.
   - {ACC} wraps the entire direct-object NP.
   - [DAT] wraps the entire dative NP or dative prepositional phrase INCLUDING the preposition.
   - <GEN> wraps the entire possessive modifier phrase INCLUDING the の/的/des/of.
4. Do NOT force-add {ACC}, [DAT], <GEN> where the role is not present.
5. Same semantic role = same bracket across all 4 languages for the same phrase.
6. Adverbs, time expressions, topic markers are NOT subjects — do not wrap them in (NOM).
   Bad: (Later,) (Dann) (Später) (今日は) — remove these (NOM) brackets.
7. Negation stays outside *verb*: "He *did* not quit" → "(He) *did* not quit" but better: "(He) *quit*-not" is wrong;
   correct form: keep the negation word outside: "(Er) *gab* nicht auf" (separable verb: *gab … auf*).
8. 把-constructions in ZH: bracket the whole object including 把: (subject) *verb* {把 + NP}.
9. Empty ( ) brackets are errors — always put the subject inside the NOM brackets.
10. Do NOT add or remove [user]/[Ninereeds] tags. Do NOT paraphrase any text.

COMMON ERRORS TO FIX:
- Missing (NOM) in Japanese (topic-drop) and Chinese sentences — identify the implied subject and add it.
- Negation words (*did not*, *nicht*, *なかった*) inside *verb* — remove them, keep only the main verb.
- Adverbs bracketed as (NOM): "(Later,)", "(Dann)", "(Später)", "(今日は)" — remove (NOM) brackets.
- {ACC} on predicate complements after "is/ist/は/是" — only bracket predicate nouns, not bare adjectives.
- <GEN> on modifier alone: "<木の>" → wrap the whole phrase: "<木の>柄".
- [DAT] on pure locatives that aren't dative in any language — use [DAT] only for dative-governed PPs.

ANNOTATED FILE TO REPAIR:
---
{content}
---

Output ONLY the corrected annotated story with the exact same [user]/[Ninereeds] structure. \
No explanation, no markdown fences, no added text. Fix every error you find."""


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


def verify_output(original: str, repaired: str, lenient: bool = False) -> str | None:
    orig_tags   = re.findall(r"\[user\]|\[Ninereeds\]", original)
    repair_tags = re.findall(r"\[user\]|\[Ninereeds\]", repaired)
    if orig_tags != repair_tags:
        return f"tag mismatch: expected {len(orig_tags)}, got {len(repair_tags)}"
    if "(" not in repaired or "*" not in repaired:
        return "annotation brackets missing"
    if not lenient and len(repaired) < len(original) * 0.8:
        return f"output too short ({len(repaired)} vs {len(original)})"
    return None


def repair_file(path: Path, api_key: str, lenient: bool = False) -> tuple[Path, bool, str]:
    original = path.read_text("utf-8")
    prompt   = REPAIR_PROMPT.replace("{content}", original)
    try:
        result = call_api(prompt, api_key)
    except Exception as e:
        return (path, False, f"API error: {e}")

    err = verify_output(original, result, lenient=lenient)
    if err:
        return (path, False, f"verify: {err}")

    path.write_text(result + "\n", "utf-8")
    return (path, True, "ok")


def files_from_audit(audit_path: Path) -> list[Path]:
    """Parse audit.md and return paths of files listed under '## Files with issues'."""
    text = audit_path.read_text("utf-8")
    # Find all ### `path` entries in the issues section
    paths = []
    in_issues = False
    for line in text.splitlines():
        if line.startswith("## Files with issues"):
            in_issues = True
            continue
        if in_issues and line.startswith("## "):
            break
        if in_issues and line.startswith("### `"):
            rel = line.strip().lstrip("### `").rstrip("`")
            p = ROOT / rel
            if p.exists():
                paths.append(p)
            else:
                print(f"  WARN: audit path not found: {rel}", file=sys.stderr)
    return paths


DONE_FILE = ROOT / "tmp" / "repair_annotations_done.txt"


def load_done() -> set[str]:
    if DONE_FILE.exists():
        return set(DONE_FILE.read_text("utf-8").splitlines())
    return set()


def mark_done(slug: str):
    with open(DONE_FILE, "a", encoding="utf-8") as f:
        f.write(slug + "\n")


def path_to_slug(p: Path) -> str:
    return str(p.relative_to(STORIES_DIR))


def cmd_run(args, api_key: str):
    lenient = getattr(args, "lenient", False)
    # Build file list
    if args.files:
        targets = [Path(f) if Path(f).is_absolute() else ROOT / f for f in args.files]
    elif getattr(args, "from_list", None):
        list_path = Path(args.from_list)
        if not list_path.exists():
            sys.exit(f"ERROR: list file not found: {list_path}")
        targets = []
        for line in list_path.read_text("utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            p = STORIES_DIR / line
            if not p.exists():
                p = ROOT / line
            if p.exists():
                targets.append(p)
            else:
                print(f"  WARN: not found: {line}", file=sys.stderr)
    elif args.all:
        targets = sorted(STORIES_DIR.rglob("*_marked.md"))
    elif args.tier:
        tier_dir = STORIES_DIR / f"tier_{args.tier}"
        targets = sorted(tier_dir.rglob("*_marked.md"))
    else:
        # Default: parse audit.md
        audit_path = ROOT / (args.from_audit or "training_data/audit.md")
        if not audit_path.exists():
            sys.exit(f"ERROR: audit file not found: {audit_path}")
        targets = files_from_audit(audit_path)
        if not targets:
            sys.exit("No files found in audit report.")

    done_slugs = load_done()
    pending = [p for p in targets if path_to_slug(p) not in done_slugs]
    skipped = len(targets) - len(pending)

    print(f"{len(targets)} files total | {skipped} already done | {len(pending)} to repair")

    if not pending:
        print("Nothing to do.")
        return

    ok = fail = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(repair_file, p, api_key, lenient): p for p in pending}
        done = skipped
        for fut in as_completed(futures):
            path, success, msg = fut.result()
            done += 1
            slug = path_to_slug(path)
            rel  = path.relative_to(STORIES_DIR)
            with _print_lock:
                if success:
                    print(f"  [{done:4d}/{len(targets)}] OK      {rel}")
                    ok += 1
                else:
                    print(f"  [{done:4d}/{len(targets)}] FAIL    {rel}: {msg}",
                          file=sys.stderr)
                    fail += 1
            if success:
                mark_done(slug)

    print(f"\nDone: {ok} repaired, {skipped} skipped, {fail} failed")
    if fail:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-audit", default="training_data/audit.md",
                        help="Path to audit.md (default: training_data/audit.md)")
    parser.add_argument("--all", action="store_true",
                        help="Repair all _marked.md files")
    parser.add_argument("--tier", type=int,
                        help="Repair only tier N files")
    parser.add_argument("--files", nargs="+",
                        help="Explicit list of _marked.md paths to repair")
    parser.add_argument("--from-list", metavar="FILE",
                        help="File containing paths to repair (one per line, relative to STORIES_DIR or repo root)")
    parser.add_argument("--lenient", action="store_true",
                        help="Skip the output-length check (use for files with bloated originals)")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("ERROR: OPENROUTER_API_KEY not set")

    cmd_run(args, api_key)


if __name__ == "__main__":
    main()
