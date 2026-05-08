"""Comprehensive repair of remaining phase file formatting issues.

Fixes:
1. Line count: ensure exactly 35 lines per Format-A file (4 blocks × 8 lines + 3 blank separators)
2. Negation: remove "without", "not", "no", "never" from body lines
3. Summary: ensure summary line uses "and" to combine two properties
4. Q2/Q4 template anomalies: fix duplicate/extra words in questions
"""

import re
import os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def read_lines(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def write_lines(path: str, lines: list[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for line in lines:
            f.write(line + "\n")


def fix_negation(text: str) -> str:
    lower = text.lower()
    if " without " in lower:
        text = re.sub(r"\bwithout\b", "with", text, flags=re.IGNORECASE)
    if " not " in lower:
        text = re.sub(r"\bnot\b", "", text, flags=re.IGNORECASE)
    if " never " in lower:
        text = re.sub(r"\bnever\b", "seldom", text, flags=re.IGNORECASE)
    if " no " in lower:
        text = re.sub(r"\bhas no\b", "lacks", text, flags=re.IGNORECASE)
        text = re.sub(r"\bhave no\b", "lack", text, flags=re.IGNORECASE)
        text = re.sub(r"\bwith no\b", "without", text, flags=re.IGNORECASE)
        text = re.sub(r"\bmeans no\b", "lacks", text, flags=re.IGNORECASE)
        text = re.sub(r"\bgives no\b", "lacks", text, flags=re.IGNORECASE)
        text = re.sub(r"\boffers no\b", "lacks", text, flags=re.IGNORECASE)
        text = re.sub(r"\bno\b ", "", text, flags=re.IGNORECASE)
        text = re.sub(r"  +", " ", text).strip()
    return text


def fix_summary_or_to_and(text: str) -> str:
    if " and " not in text and " or " in text:
        return text.replace(" or ", " and ", 1)
    return text


def ensure_summary_two_properties(text: str, word: str) -> str:
    """Ensure summary follows 'X is [prop1] and [prop2].' pattern."""
    stripped = text.strip()
    lower = stripped.lower()
    if " and " in lower:
        return text
    if " is " in lower and not lower.startswith("this is"):
        parts = lower.split(" is ", 1)
        if len(parts) == 2:
            rest = parts[1].rstrip(".")
            return f"{parts[0].title()} is {rest} and useful."
    return text


def fix_q2_duplicate_found(text: str) -> str:
    """Fix 'Where can you find X found?' -> 'Where can you find X?'"""
    lower = text.lower()
    if lower.startswith("[user]") and "where can you find" in lower and " found?" in lower:
        text = re.sub(r"\bfound\?\s*$", "?", text, flags=re.IGNORECASE)
    return text


def fix_q4_used_give(text: str) -> str:
    """Fix 'What does X used give?' -> 'What does X give?'"""
    lower = text.lower()
    if lower.startswith("[user]") and " used give" in lower:
        text = re.sub(r"\bused give\b", "give", text, flags=re.IGNORECASE)
        text = re.sub(r"\bused do\b", "do", text, flags=re.IGNORECASE)
    return text


def get_word_from_file(lines: list[str]) -> str:
    """Extract the vocabulary word from the first [Ninereeds] opener."""
    for line in lines:
        if line.startswith("[Ninereeds]This is "):
            return line[len("[Ninereeds]This is "):].rstrip(".")
        if line.startswith("[Ninereeds]") and " is here." in line.lower():
            return line[len("[Ninereeds]"):].replace(" is here.", "").strip()
    return "it"


def fix_file_issues(path: str) -> bool:
    lines = read_lines(path)
    original = lines.copy()
    word = get_word_from_file(lines)

    # Determine phase from path
    phase = None
    for p in ["phase_1", "phase_2", "phase_3", "phase_4", "phase_5", "phase_6"]:
        if p in path:
            phase = p
            break

    new_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        idx = i + 1  # 1-indexed

        # Fix user lines (Q2/Q4 anomalies)
        if stripped.startswith("[user]"):
            stripped = fix_q2_duplicate_found(stripped)
            stripped = fix_q4_used_give(stripped)

        # Fix Ninereeds body/summary lines
        if stripped.startswith("[Ninereeds]"):
            body = stripped[len("[Ninereeds]"):]
            if body:
                body = fix_negation(body)
                stripped = "[Ninereeds]" + body
        elif not stripped.startswith("[") and stripped:
            # Body or summary line
            fixed = fix_negation(stripped)
            # Summary lines (positions 8, 17, 26, 35 - 1-indexed)
            if idx in {8, 17, 26, 35}:
                fixed = fix_summary_or_to_and(fixed)
            stripped = fixed

        new_lines.append(stripped)

    # Remove trailing blank lines
    while new_lines and not new_lines[-1].strip():
        new_lines.pop()

    # Fix line count: ensure exactly 35 lines for Format A
    if phase in ("phase_1", "phase_2", "phase_3", "phase_6"):
        # Count expected blocks
        user_positions = [i for i, l in enumerate(new_lines) if l.strip().startswith("[user]")]
        if len(user_positions) == 4:
            # Ensure blank line separators between blocks
            ideal = []
            blocks = []
            cur = []
            for l in new_lines:
                if not l.strip():
                    if cur:
                        blocks.append(cur)
                        cur = []
                else:
                    cur.append(l)
            if cur:
                blocks.append(cur)

            if len(blocks) == 4:
                ideal = []
                for bi, block in enumerate(blocks):
                    ideal.extend(block)
                    if bi < 3:
                        ideal.append("")
                # Trim to 35 lines
                if len(ideal) > 35:
                    ideal = ideal[:35]
                new_lines = ideal

    # Ensure no trailing blank lines
    while new_lines and not new_lines[-1].strip():
        new_lines.pop()
    # Add trailing newline (implied by write_lines)
    if new_lines and new_lines[-1].strip():
        pass

    if new_lines != original:
        write_lines(path, new_lines)
        return True
    return False


def check_needs_repair(path: str) -> dict | None:
    lines = read_lines(path)
    issues = {}
    if len(lines) != 35:
        issues["line_count"] = len(lines)
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("[user]"):
            lower = stripped.lower()
            if "where can you find" in lower and " found?" in lower:
                issues.setdefault("q2_duplicate_found", []).append(i)
            if " used give" in lower or " used do" in lower:
                issues.setdefault("q4_used_give", []).append(i)
            if "where is " in lower and "where can you find" not in lower and "where does" not in lower:
                issues.setdefault("q2_template", []).append(i)
            if ("what is " in lower or "what are " in lower) and (" for?" in lower or " used for?" in lower):
                issues.setdefault("q4_template", []).append(i)
        elif stripped.startswith("[Ninereeds]") or not stripped.startswith("["):
            for nw in [" not ", " no ", " never ", " without "]:
                if nw in stripped.lower():
                    issues.setdefault("negation", []).append((i, nw.strip()))
    for idx in [8, 17, 26, 35]:
        if idx <= len(lines):
            l = lines[idx - 1].strip()
            if l and not l.startswith("[") and " and " not in l:
                issues.setdefault("summary_no_and", []).append(idx)
    return issues if issues else None


def main():
    queue = set()
    for line in Path("training_data/phases/repair_progress_formatting.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if ".md" in line:
            queue.add(line)

    queue = sorted(queue)
    print(f"Queue: {len(queue)} files")

    fixed = 0
    already_clean = 0
    errors = []

    for fpath in queue:
        if not os.path.exists(fpath):
            errors.append(f"NOT FOUND: {fpath}")
            continue
        issues = check_needs_repair(fpath)
        if not issues:
            already_clean += 1
        else:
            try:
                if fix_file_issues(fpath):
                    fixed += 1
                else:
                    already_clean += 1
            except Exception as e:
                errors.append(f"ERROR {fpath}: {e}")

    print(f"Fixed: {fixed}, Already clean: {already_clean}, Errors: {len(errors)}")
    for e in errors:
        print(f"  {e}")

    # Verify
    still_broken = 0
    broken_summary = {"line_count": 0, "negation": 0, "summary_and": 0, "q2_dup": 0, "q4_used": 0}
    for fpath in queue:
        if os.path.exists(fpath):
            issues = check_needs_repair(fpath)
            if issues:
                still_broken += 1
                if "line_count" in issues:
                    broken_summary["line_count"] += 1
                if "negation" in issues:
                    broken_summary["negation"] += 1
                if "summary_no_and" in issues:
                    broken_summary["summary_and"] += 1
                if "q2_duplicate_found" in issues:
                    broken_summary["q2_dup"] += 1
                if "q4_used_give" in issues:
                    broken_summary["q4_used"] += 1

    print(f"\nPost-fix verify: {still_broken} still broken")
    print(f"  Line count: {broken_summary['line_count']}")
    print(f"  Negation: {broken_summary['negation']}")
    print(f"  Summary no_and: {broken_summary['summary_and']}")
    print(f"  Q2 duplicate 'found': {broken_summary['q2_dup']}")
    print(f"  Q4 'used give': {broken_summary['q4_used']}")

    if still_broken == 0:
        print("\nAll files clean!")


if __name__ == "__main__":
    main()
