#!/usr/bin/env python3
"""
repair_philosophy.py — Reformat philosophy dialogue files.

Current format: interleaved by turn across all 4 languages, with language-suffixed tags.
  [STATEMENT_EN], [STATEMENT_DE], [STATEMENT_JA], [STATEMENT_ZH]
  [USER_EN], [USER_DE], [USER_JA], [USER_ZH]
  [NINEREEDS_EN], [Ninereeds], [Ninereeds], [Ninereeds]  ← DE/JA/ZH unlabeled by position
  ... (more turns)

Target format: full dialogue per language, plain tags, no header lines.
  [statement]        ← EN statement
  [user]             ← EN user turn 1
  [Ninereeds]        ← EN response 1
  [user]             ← EN user turn 2
  [Ninereeds]        ← EN response 2

  [statement]        ← DE statement
  ...

Language order is always EN → DE → JA → ZH.

Usage:
  python3 meta/scripts/repair_philosophy.py            # repair all files
  python3 meta/scripts/repair_philosophy.py --dry-run  # validate without writing
  python3 meta/scripts/repair_philosophy.py --verbose  # print output in dry-run
"""

import argparse
import re
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent.parent
PHIL_DIR = ROOT / "training_data" / "philosophy"

LANG_ORDER = ["EN", "DE", "JA", "ZH"]

TAG_RE = re.compile(r'^\[[\w]+\]$')


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------

def parse_blocks(text: str) -> list[tuple[str, str]]:
    """Split file into (tag, content) pairs. Header lines are dropped."""
    blocks: list[tuple[str, str]] = []
    current_tag: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("###"):
            continue
        if TAG_RE.match(stripped):
            if current_tag is not None:
                content = "\n".join(current_lines).strip()
                if content:
                    blocks.append((current_tag, content))
            current_tag = stripped
            current_lines = []
        else:
            if current_tag is not None:
                current_lines.append(line)

    if current_tag is not None:
        content = "\n".join(current_lines).strip()
        if content:
            blocks.append((current_tag, content))

    return blocks


def already_repaired(blocks: list[tuple[str, str]]) -> bool:
    """True if file is already in the target format (no language-suffixed tags)."""
    tags = {tag for tag, _ in blocks}
    return bool(tags & {"[statement]", "[user]"}) and not bool(
        tags & {"[STATEMENT_EN]", "[USER_EN]", "[NINEREEDS_EN]"}
    )


# ---------------------------------------------------------------------------
# Extract by language
# ---------------------------------------------------------------------------

def extract_by_language(blocks: list[tuple[str, str]]) -> dict | None:
    """
    Build {lang: {statement, users[], responses[]}} from parsed blocks.
    Returns None if structure is unrecognisable.
    """
    data: dict = {lang: {"statement": "", "users": [], "responses": []} for lang in LANG_ORDER}

    # After [NINEREEDS_EN], bare [Ninereeds] tags belong to DE (1), JA (2), ZH (3).
    ninereeds_idx: int | None = None

    for tag, content in blocks:
        match tag:
            case "[STATEMENT_EN]": data["EN"]["statement"] = content
            case "[STATEMENT_DE]": data["DE"]["statement"] = content
            case "[STATEMENT_JA]": data["JA"]["statement"] = content
            case "[STATEMENT_ZH]": data["ZH"]["statement"] = content

            case "[USER_EN]":
                data["EN"]["users"].append(content)
                ninereeds_idx = None  # new round
            case "[USER_DE]": data["DE"]["users"].append(content)
            case "[USER_JA]": data["JA"]["users"].append(content)
            case "[USER_ZH]": data["ZH"]["users"].append(content)

            case "[NINEREEDS_EN]":
                data["EN"]["responses"].append(content)
                ninereeds_idx = 1  # next bare tag = DE

            case "[Ninereeds]":
                if ninereeds_idx is None or ninereeds_idx >= len(LANG_ORDER):
                    return None
                data[LANG_ORDER[ninereeds_idx]]["responses"].append(content)
                ninereeds_idx += 1

            case _:
                pass  # unknown tag — tolerate silently

    return data


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

def validate(data: dict, fname: str) -> list[str]:
    """
    Valid structures per language:
      symmetric:  users == responses  (each user turn answered)
      trailing:   users == responses + 1  (closing reflection by user, no final response)
    """
    problems: list[str] = []
    turn_counts: list[int] = []

    for lang in LANG_ORDER:
        d = data[lang]
        if not d["statement"]:
            problems.append(f"{lang}: missing statement")
        nu = len(d["users"])
        nr = len(d["responses"])
        if nu == 0:
            problems.append(f"{lang}: no dialogue turns")
        elif not (nu == nr or nu == nr + 1):
            problems.append(f"{lang}: {nu} user turns but {nr} Ninereeds responses")
        turn_counts.append(nu)

    if len(set(turn_counts)) > 1:
        problems.append(f"turn-count mismatch across languages: {dict(zip(LANG_ORDER, turn_counts))}")

    return problems


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render(data: dict) -> str:
    lang_blocks: list[str] = []

    for lang in LANG_ORDER:
        d = data[lang]
        parts: list[str] = [f"[statement]\n{d['statement']}"]
        for i, user_text in enumerate(d["users"]):
            parts.append(f"[user]\n{user_text}")
            if i < len(d["responses"]):
                parts.append(f"[Ninereeds]\n{d['responses'][i]}")
        lang_blocks.append("\n\n".join(parts))

    return "\n\n".join(lang_blocks) + "\n"


# ---------------------------------------------------------------------------
# Per-file entry point
# ---------------------------------------------------------------------------

def repair_file(path: Path, dry_run: bool, verbose: bool) -> str:
    """Returns 'ok', 'already done', 'skip', or 'FAIL: <reason>'."""
    text = path.read_text(encoding="utf-8")
    blocks = parse_blocks(text)

    if not blocks:
        return "skip (empty)"

    if already_repaired(blocks):
        return "already done"

    data = extract_by_language(blocks)
    if data is None:
        return "FAIL: could not assign language to bare [Ninereeds] block"

    problems = validate(data, path.name)
    if problems:
        return "FAIL: " + "; ".join(problems)

    output = render(data)

    if dry_run:
        if verbose:
            print(f"\n--- {path.name} ---\n{output}")
        return "ok (dry-run)"

    path.write_text(output, encoding="utf-8")
    return "ok"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Repair philosophy dialogue files.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Parse and validate without writing files")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="Print rendered output during dry-run")
    args = ap.parse_args()

    files = sorted(PHIL_DIR.glob("*.md"))
    if not files:
        print(f"No .md files found in {PHIL_DIR}")
        return

    counts = {"ok": 0, "already done": 0, "skip": 0, "fail": 0}
    failures: list[tuple[str, str]] = []

    for f in files:
        result = repair_file(f, args.dry_run, args.verbose)
        if result.startswith("FAIL"):
            counts["fail"] += 1
            failures.append((f.name, result))
            print(f"  FAIL  {f.name}  —  {result[6:]}")
        elif result == "already done":
            counts["already done"] += 1
        elif result.startswith("skip"):
            counts["skip"] += 1
        else:
            counts["ok"] += 1
            if args.verbose and not args.dry_run:
                print(f"  ok    {f.name}")

    label = "dry-run" if args.dry_run else "repaired"
    print(
        f"\n{len(files)} files — {counts['ok']} {label}, "
        f"{counts['already done']} already done, "
        f"{counts['skip']} skipped, "
        f"{counts['fail']} failed"
    )

    if failures:
        print("\nFailed files:")
        for name, reason in failures:
            print(f"  {name}  —  {reason[6:]}")


if __name__ == "__main__":
    main()
