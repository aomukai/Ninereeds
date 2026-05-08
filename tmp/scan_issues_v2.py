from pathlib import Path
import re

issues = []
for f in sorted(Path('training_data/phases').rglob('*.md')):
    if 'adj_rewrites' in str(f):
        continue
    text = f.read_text(encoding='utf-8')
    lines = text.splitlines()
    if not lines:
        issues.append((str(f), 'empty file'))
        continue
    if '=== END ===' in text:
        issues.append((str(f), 'has END marker'))
    uc = text.count('[user]')
    nc = text.count('[Ninereeds]')
    if uc != nc:
        issues.append((str(f), f'unbalanced: user={uc} ninereeds={nc}'))
    if re.search(r'^```', text, re.MULTILINE):
        issues.append((str(f), 'has code fences'))
    for i, line in enumerate(lines):
        if line.strip() == '[Ninereeds]' and i+1 < len(lines) and not lines[i+1].strip():
            issues.append((str(f), f'blank Ninereeds opener at line {i+1}'))

print(f'Total issues: {len(issues)}')
for p, s in issues[:50]:
    print(f'{p}: {s}')
