#!/usr/bin/env python3
"""Check repaired nonsense files against the lang_1 English allowlist."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST = REPO_ROOT / "training_data" / "allowlist.txt"
NONSENSE_FILE = REPO_ROOT / "training_data" / "lang" / "nonsense.md"
OUT_DIR = REPO_ROOT / "training_data" / "lang" / "lang_1"
LOG_FILE = REPO_ROOT / "tmp" / "lang_1_batches" / "nonsense_repair_allowlist.log"

FUNCTION_WORDS = {
    "the", "a", "an", "is", "are", "not", "to", "of", "with", "in", "on", "at", "by",
    "can", "do", "does", "will", "has", "have", "had", "was", "were", "be", "been", "and",
    "or", "but", "so", "because", "when", "that", "this", "which", "who", "where", "how",
    "what", "also", "very", "more", "most", "some", "many", "each", "every", "all", "one",
    "two", "three", "four", "five",
}


def load_allowlist() -> set[str]:
    return {line.strip().lower() for line in ALLOWLIST.read_text(encoding="utf-8").splitlines() if line.strip()}


def parse_targets() -> list[Path]:
    paths: list[Path] = []
    for line in NONSENSE_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("| training_data/lang/lang_1/"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if not parts:
            continue
        paths.append(REPO_ROOT / parts[0])
    return paths


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z]+(?:-[a-z]+)?", text.lower())


def is_allowed_token(token: str, allowlist: set[str]) -> bool:
    if token in FUNCTION_WORDS or token in allowlist:
        return True
    if token.endswith("s") and token[:-1] in allowlist:
        return True
    if token.endswith("es") and token[:-2] in allowlist:
        return True
    if token.endswith("ies") and token[:-3] + "y" in allowlist:
        return True
    if token.endswith("ed") and token[:-2] in allowlist:
        return True
    if token.endswith("ed") and token[:-1] in allowlist:
        return True
    if token.endswith("ing") and token[:-3] in allowlist:
        return True
    if token.endswith("ing") and token[:-3] + "e" in allowlist:
        return True
    if token.endswith("er") and token[:-2] in allowlist:
        return True
    if token.endswith("est") and token[:-3] in allowlist:
        return True
    return False


def main() -> int:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    allowlist = load_allowlist()
    rows: list[str] = []

    for path in parse_targets():
        if not path.exists():
            rows.append(f"{path.relative_to(REPO_ROOT)}\tmissing file")
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines:
            rows.append(f"{path.relative_to(REPO_ROOT)}\tempty file")
            continue
        english = lines[0].strip()
        bad = [tok for tok in tokenize(english) if not is_allowed_token(tok, allowlist)]
        if bad:
            uniq = []
            seen = set()
            for tok in bad:
                if tok not in seen:
                    uniq.append(tok)
                    seen.add(tok)
            rows.append(f"{path.relative_to(REPO_ROOT)}\tunknown English token(s): {', '.join(uniq)}\t{english}")

    LOG_FILE.write_text("".join(f"{row}\n" for row in rows), encoding="utf-8")
    print(f"files checked: {len(parse_targets())}")
    print(f"allowlist issues logged: {len(rows)}")
    print("log file: tmp/lang_1_batches/nonsense_repair_allowlist.log")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
