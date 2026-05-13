"""
Fix verb files where Q1 lost its word: '[user]what is ' -> '[user]what is [xing]?'

The gerund is extracted from the first [Ninereeds] body line, which always starts
with the capitalized gerund: '[Ninereeds]Exploring is ...'
"""

import re
from pathlib import Path

BROKEN_Q1 = re.compile(r'^\[user\]what is $', re.MULTILINE)
NINEREEDS_LINE = re.compile(r'^\[Ninereeds\]([A-Z][a-z]+ing)\b', re.MULTILINE)

def fix_file(path):
    text = path.read_text(encoding="utf-8-sig")  # handle BOM
    if not BROKEN_Q1.search(text):
        return False

    # Extract gerund from first [Ninereeds] line
    m = NINEREEDS_LINE.search(text)
    if not m:
        print(f"  SKIP (can't find gerund): {path.name}")
        return False

    gerund = m.group(1).lower()
    fixed = BROKEN_Q1.sub(f'[user]what is {gerund}?', text)

    # Also fix the other three question lines if they lost their word
    # "[user]when does  happen?" -> "[user]when does [xing] happen?"
    fixed = re.sub(r'\[user\]when does  happen\?', f'[user]when does {gerund} happen?', fixed)
    fixed = re.sub(r'\[user\]what does  bring\?', f'[user]what does {gerund} bring?', fixed)
    fixed = re.sub(r'\[user\]what is  for\?', f'[user]what is {gerund} for?', fixed)

    path.write_text(fixed, encoding="utf-8")
    return True

def main():
    repo = Path(__file__).parent.parent
    fixed = 0
    skipped = 0

    for phase_dir in sorted(repo.glob("training_data/phases/phase_*/")):
        for path in sorted(phase_dir.glob("phase_*.md")):
            text = path.read_text(encoding="utf-8-sig")
            if BROKEN_Q1.search(text):
                if fix_file(path):
                    print(f"  fixed: {path.parent.name}/{path.name}")
                    fixed += 1
                else:
                    skipped += 1

    print(f"\nFixed: {fixed}  Skipped: {skipped}")

if __name__ == "__main__":
    main()
