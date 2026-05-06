#!/usr/bin/env python3

import os
import re
from collections import Counter

ROOT_FOLDER = "."
OUTPUT_FILE = "../../meta/allowed_nouns.txt"

INCLUDE_FOLDERS = {"phase_1", "phase_2", "phase_3", "phase_4", "phase_5", "phase_6"}
TEXT_EXTENSIONS = {".txt", ".md"}
SKIP_FOLDERS = {"venv", ".venv", "__pycache__", ".git"}

STOPWORDS = {
    "a", "an", "the",
    "this", "that", "these", "those",
    "is", "are", "was", "were", "be", "being", "been",
    "has", "have", "had", "does", "do", "did",
    "can", "could", "will", "would", "should", "may", "might", "must",
    "not", "very", "more", "most", "less",
    "new", "old", "good", "bad", "small", "big", "large",
    "clear", "warm", "cold", "hot",
}

def should_scan_dir(path):
    return bool(set(path.split(os.sep)) & INCLUDE_FOLDERS)


def clean_text(text):
    text = re.sub(r"^\[user\].*$", " ", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"\[ninereeds\]", " ", text, flags=re.IGNORECASE)
    return text.lower()


def add_match(counter, word):
    word = word.strip().lower()

    if not re.fullmatch(r"[a-z][a-z\-]*", word):
        return

    if len(word) < 3:
        return

    if word in STOPWORDS:
        return

    # Conservative: skip likely plurals and third-person verbs.
    # This removes noise like keeps, stays, happens, brings, gives, makes.
    # It also skips real nouns like grass/glass, but that is safer for a whitelist.
    if word.endswith("s"):
        return

    counter[word] += 1


def extract_nouns_from_frames(text, counter):
    text = clean_text(text)

    patterns = [
        r"\bthis is (?:a|an|the) ([a-z][a-z\-]*)\b",
        r"\bthat is (?:a|an|the) ([a-z][a-z\-]*)\b",
        r"\bit is (?:a|an|the) ([a-z][a-z\-]*)\b",

        r"\b(?:a|an|the) ([a-z][a-z\-]*) is\b",
        r"\b(?:a|an|the) ([a-z][a-z\-]*) has\b",
        r"\b(?:a|an|the) ([a-z][a-z\-]*) can\b",

        r"\b([a-z][a-z\-]*) is a thing\b",
        r"\b([a-z][a-z\-]*) is a person\b",
        r"\b([a-z][a-z\-]*) is an animal\b",
        r"\b([a-z][a-z\-]*) is a place\b",
        r"\b([a-z][a-z\-]*) is a body part\b",
        r"\b([a-z][a-z\-]*) is food\b",
        r"\b([a-z][a-z\-]*) is water\b",
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, text):
            add_match(counter, match.group(1))


def main():
    counter = Counter()
    scanned_files = 0

    for root, dirs, files in os.walk(ROOT_FOLDER):
        dirs[:] = [
            d for d in dirs
            if d not in SKIP_FOLDERS and not d.startswith(".")
        ]

        if not should_scan_dir(root):
            continue

        for filename in files:
            if os.path.splitext(filename)[1].lower() not in TEXT_EXTENSIONS:
                continue

            path = os.path.join(root, filename)

            try:
                with open(path, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue

            print(f"Scanning: {path}")
            extract_nouns_from_frames(text, counter)
            scanned_files += 1

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for word, count in sorted(counter.items(), key=lambda x: (-x[1], x[0])):
            f.write(f"{word}\t{count}\n")

    print()
    print("Done.")
    print(f"Scanned files: {scanned_files}")
    print(f"Unique safe nouns: {len(counter)}")
    print(f"Output written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
