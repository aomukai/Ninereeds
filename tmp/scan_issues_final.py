import re, sys
from pathlib import Path

issues = []
for p in sorted(Path('training_data/phases').rglob('phase_*.md')):
    text = p.read_text('utf-8')
    lines = text.split('\n')
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if stripped == '[Ninereeds]' and i+1 < len(lines) and lines[i+1].strip() == '':
            issues.append('BLANK ' + p.relative_to(Path('.').resolve()).as_posix() + ':' + str(i+1))
            break
    if '=== END ===' in text:
        issues.append('ENDMARKER ' + p.relative_to(Path('.').resolve()).as_posix())
    if re.search(r'^```\s*$', text, re.MULTILINE):
        issues.append('FENCE ' + p.relative_to(Path('.').resolve()).as_posix())

if issues:
    for i in issues:
        print(i)
    sys.exit(1)
else:
    print('ALL PHASE FILES CLEAN')
