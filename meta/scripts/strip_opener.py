"""
Strip the "This is X." opener from every Format A phase file.

Before:
  [Ninereeds]This is a hat.
  The hat is soft or hard.
  ...

After:
  [Ninereeds]A hat is soft or hard.
  The hat has a round shape.
  ...

Format B files (opener is "[X] is here.") are left untouched.
"""

import re
import sys
from pathlib import Path

VOWELS = set("aeiouAEIOU")

def indefinite_article(word):
    """Return 'An' if word starts with a vowel sound, else 'A'."""
    return "An" if word and word[0] in VOWELS else "A"

def transform_block_line(ninereeds_line, first_body_line):
    """
    ninereeds_line  : '[Ninereeds]This is a hat.'
    first_body_line : 'The hat is soft or hard.'
    returns         : '[Ninereeds]A hat is soft or hard.'
    """
    # Strip leading 'The ' and replace with 'A/An '
    if first_body_line.startswith("The "):
        rest = first_body_line[4:]          # 'hat is soft or hard.'
        first_word = rest.split()[0] if rest.split() else ""
        article = indefinite_article(first_word)
        new_first = f"{article} {rest}"
    else:
        # Already starts with the bare word or another article — keep as-is
        new_first = first_body_line

    return f"[Ninereeds]{new_first}"

def transform_file(text):
    """
    Transform all Format A [Ninereeds] blocks in a file's text.
    Returns (new_text, changed: bool).
    """
    lines = text.splitlines(keepends=True)
    out = []
    i = 0
    changed = False

    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip("\r\n")

        # Detect Format A opener: '[Ninereeds]This is ...'
        if stripped.startswith("[Ninereeds]This is "):
            # Next line is the first body line
            if i + 1 < len(lines):
                first_body = lines[i + 1].rstrip("\r\n")
                new_ninereeds = transform_block_line(stripped, first_body)
                # Preserve original line ending from the first body line
                ending = "\n"
                out.append(new_ninereeds + ending)
                i += 2          # skip both opener and first body line
                changed = True
                continue
            # Edge case: opener at end of file with no body — keep as-is
        elif stripped.startswith("[Ninereeds]") and "is here." in stripped:
            # Format B — pass through untouched
            pass

        out.append(line)
        i += 1

    return "".join(out), changed

def main(dry_run=True, sample=5):
    repo = Path(__file__).parent.parent
    phase_dirs = sorted(repo.glob("training_data/phases/phase_*/"))
    files = []
    for d in phase_dirs:
        files.extend(sorted(d.glob("phase_*.md")))

    changed_files = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        new_text, changed = transform_file(text)
        if changed:
            changed_files.append((path, new_text))

    print(f"Files to change: {len(changed_files)} / {len(files)} total")

    if dry_run and sample:
        print(f"\n--- DRY RUN: first {sample} changed files ---\n")
        for path, new_text in changed_files[:sample]:
            print(f"=== {path.name} ===")
            print(new_text[:600])
            print()
        return

    # Apply changes
    for path, new_text in changed_files:
        path.write_text(new_text, encoding="utf-8")
    print(f"Done. {len(changed_files)} files updated.")

if __name__ == "__main__":
    dry = "--apply" not in sys.argv
    main(dry_run=dry, sample=5 if dry else 0)
