#!/usr/bin/env python3
"""
repair_annotations_nim.py — Repair _marked.md annotation errors via NVIDIA NIM (DeepSeek V4 Pro).

Uses the same repair prompt as repair_annotations.py but hits the NIM free endpoint.
Reads NVIDIA_API_KEY from environment (or OPENROUTER_API_KEY as fallback for testing).
Skips files already fixed by the DeepSeek pass or the codex medium pass.

Sources:
  --failed-only   parse tmp/repair_annotations_full_run.log for FAIL entries (default)
  --all           all _marked.md files
  --files f ...   explicit list

Usage:
  NVIDIA_API_KEY=nvapi-xxx python3 meta/scripts/repair_annotations_nim.py --failed-only --workers 3
  NVIDIA_API_KEY=nvapi-xxx python3 meta/scripts/repair_annotations_nim.py --all --workers 3
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
FAIL_LOG    = ROOT / "tmp" / "repair_annotations_full_run.log"
DONE_FILE   = ROOT / "tmp" / "repair_nim_done.txt"

# Also skip files already handled by prior passes
PRIOR_DONE = [
    ROOT / "tmp" / "repair_codex_medium_done.txt",
]

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
NIM_MODEL    = "deepseek-ai/deepseek-v4-pro"
MAX_TOKENS   = 16384
TEMPERATURE  = 0.2

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
7. Negation stays outside *verb*: correct form: "(Er) *gab* nicht auf" (separable verb: *gab … auf*).
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


def verify_output(original: str, repaired: str) -> str | None:
    orig_tags   = re.findall(r"\[user\]|\[Ninereeds\]", original)
    repair_tags = re.findall(r"\[user\]|\[Ninereeds\]", repaired)
    if orig_tags != repair_tags:
        return f"tag mismatch: expected {len(orig_tags)}, got {len(repair_tags)}"
    if "(" not in repaired or "*" not in repaired:
        return "annotation brackets missing"
    if len(repaired) < len(original) * 0.8:
        return f"output too short ({len(repaired)} vs {len(original)})"
    return None


def repair_file(path: Path, api_key: str) -> tuple[Path, bool, str]:
    original = path.read_text("utf-8")
    prompt   = REPAIR_PROMPT.replace("{content}", original)
    try:
        result = call_api(prompt, api_key)
    except Exception as e:
        return path, False, f"API error: {e}"

    err = verify_output(original, result)
    if err:
        return path, False, f"verify: {err}"

    path.write_text(result + "\n", "utf-8")
    return path, True, "ok"


def load_done() -> set[str]:
    slugs: set[str] = set()
    if DONE_FILE.exists():
        slugs |= set(DONE_FILE.read_text("utf-8").splitlines())
    for prior in PRIOR_DONE:
        if prior.exists():
            slugs |= set(prior.read_text("utf-8").splitlines())
    return slugs


def mark_done(slug: str) -> None:
    with open(DONE_FILE, "a", encoding="utf-8") as f:
        f.write(slug + "\n")


def path_to_slug(p: Path) -> str:
    return str(p.relative_to(STORIES_DIR))


def files_from_fail_log(log_path: Path) -> list[Path]:
    if not log_path.exists():
        sys.exit(f"ERROR: fail log not found: {log_path}")
    paths: list[Path] = []
    seen: set[str] = set()
    for line in log_path.read_text("utf-8", errors="replace").splitlines():
        if "FAIL" not in line:
            continue
        m = re.search(r"FAIL\s+(tier_\S+_marked\.md)", line)
        if not m:
            continue
        rel = m.group(1).split(":")[0].strip()
        if rel in seen:
            continue
        seen.add(rel)
        p = STORIES_DIR / rel
        if p.exists():
            paths.append(p)
        else:
            print(f"  WARN: not found: {rel}", file=sys.stderr)
    return paths


def cmd_run(args, api_key: str) -> None:
    if args.files:
        targets = [Path(f) if Path(f).is_absolute() else ROOT / f for f in args.files]
    elif args.all:
        targets = sorted(STORIES_DIR.rglob("*_marked.md"))
    else:
        targets = files_from_fail_log(FAIL_LOG)
        if not targets:
            print("No failed files found in log. Use --all to process everything.")
            return

    done_slugs = load_done()
    pending    = [p for p in targets if path_to_slug(p) not in done_slugs]
    skipped    = len(targets) - len(pending)

    print(f"Model: {NIM_MODEL} | {len(targets)} files | {skipped} already done | {len(pending)} to repair")
    if not pending:
        print("Nothing to do.")
        return

    ok = fail = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(repair_file, p, api_key): p for p in pending}
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
        description="Repair _marked.md annotation errors via NVIDIA NIM (DeepSeek V4 Pro)."
    )
    parser.add_argument("--failed-only", action="store_true",
                        help="Only process files that failed the DeepSeek pass (default)")
    parser.add_argument("--all", action="store_true",
                        help="Process all _marked.md files")
    parser.add_argument("--files", nargs="+",
                        help="Explicit list of _marked.md paths")
    parser.add_argument("--workers", type=int, default=3,
                        help="Parallel workers (default: 3 — conservative for rate limits)")
    args = parser.parse_args()

    api_key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("ERROR: NVIDIA_API_KEY not set")

    cmd_run(args, api_key)


if __name__ == "__main__":
    main()
