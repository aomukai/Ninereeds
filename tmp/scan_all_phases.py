import re, sys
from pathlib import Path
R = Path(r'D:\Ninereeds')
issues = []
for p in sorted(R.glob('training_data/phases/phase_*/phase_*.md')):
    text = p.read_text('utf-8')
    lines = text.split('\n')
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if stripped == '[Ninereeds]' and i+1 < len(lines) and lines[i+1].strip() == '':
            issues.append('BLANK ' + p.name + ':' + str(i+1))
    if '=== END ===' in text:
        issues.append('ENDMARKER ' + p.name)
    if re.search(r'^```\s*$', text, re.MULTILINE):
        issues.append('FENCE ' + p.name)
    uc = len(re.findall(r'^\[user\]', text, re.MULTILINE))
    nc = len(re.findall(r'^\[Ninereeds\]', text, re.MULTILINE))
    if uc != 4 or nc != 4:
        issues.append('TAGMISMATCH ' + p.name + ' u=' + str(uc) + ' n=' + str(nc))
    if '[user]' not in text or '[Ninereeds]' not in text:
        issues.append('MISSING_TAGS ' + p.name)
if issues:
    for i in issues:
        print(i)
    sys.exit(1)
else:
    print('ALL CLEAN')
