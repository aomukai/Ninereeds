"""
Fix two issues in verb files:

1. ORPHAN BODY LINES: lines in [Ninereeds] blocks that start with lowercase,
   missing the "Xing is/happens/brings/is for" subject prefix.
   Fix: prepend "Gerund is " (using gerund extracted from [Ninereeds] tag line).

2. Q2 MISSING-WITH SUMMARY: summary lines of the form
   "Xing happens word and word." (no preposition before the noun pair).
   Fix: insert "with " to make "Xing happens with word and word."

Operates only on files listed in training_data/phases/verbs.txt.
"""

import re
from pathlib import Path

NINEREEDS_GERUND = re.compile(r'^\[Ninereeds\]([A-Z][a-z]+ing)\b')
ORPHAN_LINE = re.compile(r'^[a-z]')
Q2_MISSING_WITH = re.compile(r'^([A-Z][a-z]+ing happens )([a-z]+ and [a-z]+\.)$')


def fix_file(path):
    text = path.read_text(encoding='utf-8-sig')
    lines = text.splitlines()
    changed = False

    # Extract gerund from first [Ninereeds] line
    gerund = None
    for line in lines:
        m = NINEREEDS_GERUND.match(line)
        if m:
            gerund = m.group(1)
            break

    if not gerund:
        print(f'  SKIP (no gerund found): {path.name}')
        return False

    new_lines = []
    for line in lines:
        # Fix orphan body lines
        if line and ORPHAN_LINE.match(line) and not line.startswith('['):
            fixed_line = gerund + ' is ' + line
            new_lines.append(fixed_line)
            changed = True
            continue

        # Fix Q2 missing-with summary
        m = Q2_MISSING_WITH.match(line)
        if m:
            fixed_line = m.group(1) + 'with ' + m.group(2)
            new_lines.append(fixed_line)
            changed = True
            continue

        new_lines.append(line)

    if changed:
        # Preserve trailing newline if original had one
        ending = '\n' if text.endswith('\n') else ''
        path.write_text('\n'.join(new_lines) + ending, encoding='utf-8')

    return changed


def main():
    repo = Path(__file__).parent.parent
    verbs_file = repo / 'training_data/phases/verbs.txt'
    verbs = [
        l.strip().split('\t')[0]
        for l in verbs_file.read_text().splitlines()
        if l.strip() and not l.startswith('#')
    ]

    fixed = 0
    skipped = 0
    for v in verbs:
        path = repo / 'training_data/phases' / v
        if not path.exists():
            skipped += 1
            continue
        if fix_file(path):
            print(f'  fixed: {v}')
            fixed += 1

    print(f'\nFixed: {fixed}  Skipped: {skipped}')


if __name__ == '__main__':
    main()
