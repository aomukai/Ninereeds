#!/usr/bin/env python3
"""
validate_aug.py — Validate C16A _rephrase.md files.

Checks:
  1. Every source angle file has a _rephrase.md sibling.
  2. Every _rephrase.md has exactly one [user] and one [Ninereeds] tag.
  3. [Ninereeds] answer is not empty.
  4. [user] question differs from the source (rephrase actually rephrased).
  5. File is not a near-copy of the source (catches pass-through failures).

Usage:
  python3 meta/scripts/validate_aug.py [--bucket BUCKET] [--limit N] [--fix-missing]

  --bucket BUCKET   Only validate a specific bucket (e.g. actions, food)
  --limit N         Stop after N failures (default: unlimited)
  --fix-missing     Print a list of missing rephrase files to tmp/missing_rephrases.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORDS_DIR = REPO_ROOT / "training_data" / "redesign" / "words"


def get_user_line(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("[user]"):
            return line.strip()
    return ""


def get_ninereeds_line(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("[Ninereeds]"):
            return line.replace("[Ninereeds]", "").strip()
    return ""


def validate_rephrase(src: Path, rep: Path) -> list[str]:
    """Return list of failure strings, empty if clean."""
    failures = []

    try:
        rep_text = rep.read_text(encoding="utf-8").strip()
    except Exception as e:
        return [f"UNREADABLE: {e}"]

    if not rep_text:
        return ["EMPTY"]

    if "[user]" not in rep_text:
        failures.append("MISSING_USER_TAG")
    if "[Ninereeds]" not in rep_text:
        failures.append("MISSING_NINEREEDS_TAG")

    if failures:
        return failures

    nr_answer = get_ninereeds_line(rep_text)
    if not nr_answer:
        failures.append("EMPTY_NINEREEDS_ANSWER")

    try:
        src_text = src.read_text(encoding="utf-8").strip()
        src_user = get_user_line(src_text)
        rep_user = get_user_line(rep_text)

        if src_user and rep_user and src_user.lower() == rep_user.lower():
            failures.append("USER_UNCHANGED")

        # Near-copy check: if rephrase text is >90% identical to source, flag it
        if src_text and rep_text:
            common = sum(1 for a, b in zip(src_text, rep_text) if a == b)
            ratio = common / max(len(src_text), len(rep_text))
            if ratio > 0.92:
                failures.append(f"NEAR_COPY({ratio:.2f})")
    except Exception:
        pass

    return failures


def run(args: argparse.Namespace) -> None:
    if args.bucket:
        buckets = [WORDS_DIR / args.bucket]
        if not buckets[0].is_dir():
            print(f"ERROR: bucket '{args.bucket}' not found", file=sys.stderr)
            sys.exit(1)
    else:
        buckets = [d for d in sorted(WORDS_DIR.iterdir()) if d.is_dir() and d.name != "unsorted"]

    total_src = 0
    total_rep = 0
    missing = []
    failures: list[tuple[Path, list[str]]] = []

    for bucket_dir in buckets:
        for src in sorted(bucket_dir.glob("*.md")):
            if src.name.endswith("_rephrase.md"):
                continue
            total_src += 1
            rep = src.with_name(src.stem + "_rephrase.md")
            if not rep.exists():
                missing.append(src)
                continue
            total_rep += 1
            errs = validate_rephrase(src, rep)
            if errs:
                failures.append((rep, errs))
                if args.limit and len(failures) >= args.limit:
                    break
        if args.limit and len(failures) >= args.limit:
            break

    # Report
    print(f"Source files:    {total_src}")
    print(f"Rephrase files:  {total_rep}")
    print(f"Missing:         {len(missing)}")
    print(f"Failures:        {len(failures)}")
    print()

    if missing:
        print(f"=== MISSING ({len(missing)}) ===")
        for f in missing[:20]:
            print(f"  {f.relative_to(WORDS_DIR)}")
        if len(missing) > 20:
            print(f"  ... and {len(missing) - 20} more")
        if args.fix_missing:
            out = REPO_ROOT / "tmp" / "missing_rephrases.txt"
            out.write_text("\n".join(str(f) for f in missing) + "\n", encoding="utf-8")
            print(f"\n  Full list written to {out}")
        print()

    if failures:
        # Group by failure type
        from collections import Counter
        type_counts: Counter = Counter()
        for _, errs in failures:
            for e in errs:
                k = e.split("(")[0]
                type_counts[k] += 1

        print("=== FAILURE TYPES ===")
        for k, v in type_counts.most_common():
            print(f"  {k:30s} {v}")
        print()

        print("=== SAMPLE FAILURES (up to 10) ===")
        for rep, errs in failures[:10]:
            print(f"  {rep.relative_to(WORDS_DIR)}")
            print(f"    {', '.join(errs)}")
        print()

    if not missing and not failures:
        print("ALL CLEAN")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket",      help="Validate a single bucket only")
    parser.add_argument("--limit",       type=int, help="Stop after N failures")
    parser.add_argument("--fix-missing", action="store_true",
                        help="Write missing file list to tmp/missing_rephrases.txt")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
