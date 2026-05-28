#!/usr/bin/env python3
"""
fix_grammar_punctuation.py — Fix CJK sentence termination in grammar training files.

Two patterns fixed:
  1. CJK line ends with ASCII '.' → replace with '。'
  2. CJK statement line has no terminal punctuation → append '。'

Skips: [user]/[Ninereeds] tags, EN/DE lines, question lines, structural markers.
Dry-run by default. Pass --fix to write changes.

Usage:
  python3 meta/scripts/fix_grammar_punctuation.py          # dry run
  python3 meta/scripts/fix_grammar_punctuation.py --fix    # apply
"""

from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GRAMMAR = ROOT / "training_data" / "grammar"

CJK_RE = re.compile(r"[一-鿿぀-ヿ㐀-䶿]")

SKIP_PREFIXES = ("[user]", "[Ninereeds]", "#", "(SECTION")
TERMINAL = ("。", "」", "』", "）")


def is_cjk_line(s: str) -> bool:
    return bool(CJK_RE.search(s))


def needs_fix(s: str) -> str | None:
    """Return the fixed line, or None if no fix needed."""
    s = s.rstrip()  # strip trailing spaces before all checks
    if not s or any(s.startswith(p) for p in SKIP_PREFIXES):
        return None
    if s.endswith("?") or "/" in s:
        return None
    if s.startswith(("(", "[", "{")):
        return None
    if not is_cjk_line(s):
        return None
    if any(s.endswith(t) for t in TERMINAL):
        return None  # already correct
    if s.endswith("."):
        return s[:-1] + "。"  # ASCII period → CJK period
    return s + "。"  # missing period entirely


def process_file(path: Path, apply: bool) -> list[tuple[str, str]]:
    """Return list of (old_line, new_line) changes."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    changes = []
    new_lines = []
    for line in lines:
        stripped = line.rstrip("\n\r")
        fixed = needs_fix(stripped)
        if fixed is not None:
            changes.append((stripped, fixed))
            new_lines.append(fixed + "\n")
        else:
            new_lines.append(line)

    if changes and apply:
        path.write_text("".join(new_lines), encoding="utf-8")

    return changes


def main() -> None:
    apply = "--fix" in sys.argv
    mode = "FIXING" if apply else "DRY RUN"
    print(f"{mode} — grammar punctuation check\n")

    total_files = total_changes = 0

    for f in sorted(GRAMMAR.rglob("*.md")):
        if f.parent == GRAMMAR:
            continue  # skip design docs at root level
        changes = process_file(f, apply)
        if changes:
            total_files += 1
            total_changes += len(changes)
            print(f"{f.relative_to(GRAMMAR)} ({len(changes)} fix{'es' if len(changes) > 1 else ''}):")
            for old, new in changes:
                print(f"  - {old!r}")
                print(f"  + {new!r}")

    print(f"\n{'Fixed' if apply else 'Would fix'} {total_changes} lines in {total_files} files.")
    if not apply:
        print("Run with --fix to apply.")


if __name__ == "__main__":
    main()
