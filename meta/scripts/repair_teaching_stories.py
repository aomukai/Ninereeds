#!/usr/bin/env python3
"""
repair_teaching_stories.py — Apply fixes from the audit report.

Two repair strategies:
  substitution  — string replacement, no LLM needed (Simplified Chinese chars,
                  exact grammar corrections flagged by audit)
  rewrite_block — send the problematic language block to a cheap LLM for rewrite

Usage:
  # Dry run (show what would change):
  python3 meta/scripts/repair_teaching_stories.py --dry-run

  # Apply substitutions only (no LLM):
  python3 meta/scripts/repair_teaching_stories.py --subs-only

  # Full repair (substitutions + LLM rewrites):
  python3 meta/scripts/repair_teaching_stories.py [--workers 4] [--model ...]

  # Single file:
  python3 meta/scripts/repair_teaching_stories.py --label worry

Reads:   tmp/teaching_stories_audit.jsonl
Writes:  training_data/teaching_stories/<label>.md  (in place)
Progress: tmp/repair_done.txt
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent.parent

_env = ROOT / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if _line.strip() and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

AUDIT_LOG    = ROOT / "tmp" / "teaching_stories_audit.jsonl"
STORIES_DIR  = ROOT / "training_data" / "teaching_stories"
REPAIR_DONE  = ROOT / "tmp" / "repair_done.txt"
REPAIR_FAILS = ROOT / "tmp" / "repair_failed.txt"

LOCAL_ENDPOINT  = "http://192.168.3.5:1234/v1"
REMOTE_ENDPOINT = "https://openrouter.ai/api/v1"
REPAIR_MODEL    = "deepseek/deepseek-chat-v3-0324"   # override with --model

# ---------------------------------------------------------------------------
# Language block extraction
# ---------------------------------------------------------------------------
LANG_ORDER = ["EN", "DE", "JP", "ZH"]


def split_blocks(text: str) -> list[str]:
    """Split file into 4 language blocks (each starts at [user])."""
    lines   = text.splitlines(keepends=True)
    blocks  = []
    current = []
    for line in lines:
        if line.startswith("[user]") and current:
            # Count [user] tags already in current — if this is a new block
            user_count = sum(1 for l in current if l.startswith("[user]"))
            if user_count >= 1:
                blocks.append("".join(current))
                current = []
        current.append(line)
    if current:
        blocks.append("".join(current))
    return blocks


def join_blocks(blocks: list[str]) -> str:
    return "\n".join(b.rstrip("\n") for b in blocks) + "\n"


def lang_of_block(block: str) -> str:
    user_line = next((l for l in block.splitlines() if l.startswith("[user]")), "")
    content   = user_line[6:].strip()
    jp_chars  = sum(1 for c in content if '぀' <= c <= 'ヿ')
    cjk_chars = sum(1 for c in content if '一' <= c <= '鿿')
    if jp_chars > 0:
        return "JP"
    if cjk_chars > 0:
        return "ZH"
    de_markers = ["was", "wie", "ist", "ein", "eine", "der", "die", "das",
                  "kannst", "warum", "wann", "bitte", "zeig"]
    lower = content.lower()
    if any(f" {m} " in f" {lower} " for m in de_markers):
        return "DE"
    return "EN"


# ---------------------------------------------------------------------------
# Substitution repair (no LLM)
# ---------------------------------------------------------------------------

def apply_substitutions(text: str, issues: list[dict]) -> str:
    for issue in issues:
        if issue.get("repair_type") != "substitution":
            continue
        # Simplified Chinese: use stored simp_map if present
        if issue["issue_type"] == "simplified_chinese":
            simp_map = issue.get("simp_map", {})
            if not simp_map:
                # Parse from flagged_text "什么→什麼, 这→這"
                for pair in issue.get("flagged_text", "").split(","):
                    pair = pair.strip()
                    if "→" in pair:
                        s, t = pair.split("→", 1)
                        simp_map[s.strip()] = t.strip()
            for simp, trad in simp_map.items():
                text = text.replace(simp, trad)
        else:
            # Direct string replacement
            flagged    = issue.get("flagged_text", "")
            suggestion = issue.get("suggestion", "")
            if flagged and suggestion and flagged != suggestion:
                text = text.replace(flagged, suggestion, 1)
    return text


# ---------------------------------------------------------------------------
# LLM rewrite for one block
# ---------------------------------------------------------------------------

REWRITE_PROMPT = """\
You are repairing one language block of a 4-language teaching story file.
The block is the {lang} version of a story teaching the concept "{label}".

ISSUES TO FIX:
{issues_list}

RULES:
- Return only the corrected block content (the [user] line and [Ninereeds] response).
- Preserve the [user] and [Ninereeds] tags exactly.
- Do not add explanation or extra text.
- If the issue is "polite_japanese": rewrite all です/ます/でした/ました to plain form.
- If the issue is "definition_opener": replace the opening definition with a narrative scene.
- If the issue is "internal_state": replace direct emotion statement with observable behavior.

ORIGINAL BLOCK:
{block}
"""


def rewrite_block(block: str, lang: str, label: str,
                  issues: list[dict], client: OpenAI, model: str) -> str:
    issues_text = "\n".join(
        f"- [{i['issue_type']}] {i['flagged_text']} → {i['suggestion']}"
        for i in issues
    )
    prompt = REWRITE_PROMPT.format(
        lang=lang, label=label,
        issues_list=issues_text,
        block=block.strip(),
    )
    try:
        resp = client.chat.completions.create(
            model=model,
            max_tokens=1024,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        result = resp.choices[0].message.content
        if not result:
            raise RuntimeError(f"Model returned null/empty content")
        result = result.strip()
        # Strip accidental fences
        if result.startswith("```"):
            result = "\n".join(l for l in result.splitlines()
                               if not l.startswith("```")).strip()
        return result + "\n"
    except Exception as e:
        raise RuntimeError(f"LLM rewrite failed for {lang}: {e}")


# ---------------------------------------------------------------------------
# Main repair worker
# ---------------------------------------------------------------------------

def repair_file(record: dict, client: OpenAI | None, model: str,
                subs_only: bool, dry_run: bool) -> bool:
    rel_path = record["file"]
    path     = ROOT / rel_path
    label    = record["label"]
    issues   = record["issues"]

    if not path.exists():
        print(f"  SKIP (missing): {path.name}")
        return False

    text = path.read_text(encoding="utf-8")

    # Pass 1: substitutions (no LLM)
    sub_issues = [i for i in issues if i.get("repair_type") == "substitution"]
    text = apply_substitutions(text, sub_issues)

    if subs_only:
        if not dry_run and sub_issues:
            path.write_text(text, encoding="utf-8")
            print(f"  SUB {path.name} ({len(sub_issues)} substitutions)")
        elif dry_run:
            print(f"  DRY {path.name} — {len(sub_issues)} substitutions")
        return True

    # Pass 2: LLM rewrites
    rewrite_issues = [i for i in issues if i.get("repair_type") == "rewrite_block"]
    if rewrite_issues and client:
        blocks = split_blocks(text)
        if len(blocks) != 4:
            print(f"  SKIP (bad block count {len(blocks)}): {path.name}")
            return False

        by_lang: dict[str, list[dict]] = {}
        for issue in rewrite_issues:
            by_lang.setdefault(issue["lang"], []).append(issue)

        for i, block in enumerate(blocks):
            block_lang = lang_of_block(block)
            if block_lang not in by_lang:
                # Try positional fallback
                if LANG_ORDER[i] in by_lang:
                    block_lang = LANG_ORDER[i]
                else:
                    continue
            try:
                blocks[i] = rewrite_block(
                    block, block_lang, label,
                    by_lang[block_lang], client, model,
                )
            except Exception as e:
                print(f"  REWRITE ERROR {path.name} [{block_lang}]: {e}")
                return False

        text = join_blocks(blocks)

    if not dry_run:
        path.write_text(text, encoding="utf-8")
        print(f"  FIXED {path.name} "
              f"(subs={len(sub_issues)}, rewrites={len(rewrite_issues)})")
    else:
        print(f"  DRY   {path.name} — "
              f"{len(sub_issues)} subs, {len(rewrite_issues)} rewrites")
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label",     help="Repair one concept only")
    ap.add_argument("--dry-run",   action="store_true", help="Show changes, don't write")
    ap.add_argument("--subs-only", action="store_true", help="Substitutions only, no LLM")
    ap.add_argument("--local",     action="store_true", help="Use local LM Studio")
    ap.add_argument("--endpoint",  help="Override endpoint URL")
    ap.add_argument("--model",     help="Override model name")
    ap.add_argument("--workers",   type=int, default=4)
    ap.add_argument("--force",     action="store_true",
                    help="Re-repair already-repaired files")
    args = ap.parse_args()

    if not AUDIT_LOG.exists():
        sys.exit("No audit log found. Run audit_teaching_stories.py first.")

    records = [json.loads(l) for l in AUDIT_LOG.read_text().splitlines() if l.strip()]

    if args.label:
        records = [r for r in records if r["label"] == args.label]
        if not records:
            sys.exit(f"No audit record for '{args.label}'")

    done: set[str] = set()
    if REPAIR_DONE.exists() and not args.force:
        done = set(REPAIR_DONE.read_text().splitlines())
    records = [r for r in records if r["file"] not in done]

    if not records:
        print("Nothing to repair — all flagged files already processed.")
        return

    client = None
    model  = args.model or REPAIR_MODEL
    if not args.subs_only and not args.dry_run:
        if args.local or args.endpoint:
            url = args.endpoint or LOCAL_ENDPOINT
            client = OpenAI(base_url=url, api_key="local")
        else:
            key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
            if not key:
                sys.exit("Set OPENROUTER_API_KEY or use --local / --subs-only.")
            client = OpenAI(base_url=REMOTE_ENDPOINT, api_key=key)

    print(f"Repairing {len(records)} files  "
          f"({'dry run' if args.dry_run else 'live'}, "
          f"{'subs only' if args.subs_only else f'model={model}'}, "
          f"workers={args.workers})")

    lock = threading.Lock()
    ok = fail = 0

    def process(record: dict):
        nonlocal ok, fail
        success = repair_file(record, client, model, args.subs_only, args.dry_run)
        with lock:
            if success:
                ok += 1
                if not args.dry_run:
                    with open(REPAIR_DONE, "a") as f:
                        f.write(record["file"] + "\n")
            else:
                fail += 1
                with open(REPAIR_FAILS, "a") as f:
                    f.write(record["file"] + "\n")

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process, r): r for r in records}
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as e:
                print(f"  EXCEPTION: {e}")

    print(f"\nDone. ✓ {ok}  ✗ {fail}")
    if fail:
        print(f"Failed list: {REPAIR_FAILS}")


if __name__ == "__main__":
    main()
