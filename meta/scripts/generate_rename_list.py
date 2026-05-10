#!/usr/bin/env python3
"""
Generate a rename lookup file for all training_data/phases files.
Output format (one line per file):
    training_data/phases/phase_1/phase_1_001.md\t[user]What does the sun look like?

Only the first [user] line is included — enough for DeepSeek to identify the target word.
Output written to tmp/rename_list.txt.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PHASES_DIR = REPO / "training_data" / "phases"
OUT = REPO / "tmp" / "rename_list.txt"


def first_user_line(path):
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("[user]"):
            return line.strip()
    return ""


def sort_key(path):
    # Sort by phase number, then by embedded number in filename
    phase_m = re.search(r"phase_(\d+)", path.parent.name)
    phase_n = int(phase_m.group(1)) if phase_m else 0
    num_m = re.search(r"(\d+)", path.stem)
    file_n = int(num_m.group(1)) if num_m else 0
    return (phase_n, file_n, path.name)


rows = []
for md in PHASES_DIR.rglob("*.md"):
    rel = md.relative_to(REPO)
    user_line = first_user_line(md)
    if user_line:
        rows.append((md, str(rel), user_line))

rows.sort(key=lambda r: sort_key(r[0]))

OUT.parent.mkdir(exist_ok=True)
with OUT.open("w", encoding="utf-8") as fh:
    for _, rel, user_line in rows:
        fh.write(f"{rel}\t{user_line}\n")

print(f"Written {len(rows)} entries to {OUT}")
