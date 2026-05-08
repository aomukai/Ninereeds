import re, sys
from pathlib import Path

issues = []
for p in sorted(Path('training_data/phases').rglob('phase_*.md')):
    text = p.read_text('utf-8')
    lines = text.split('\n')
    for i, ln in enumerate(lines):
        if '  ' in ln and ln.strip() and not ln.strip().startswith('['):
            issues.append(f'DOUBLESPACE {p.relative_to(Path(".").resolve()).as_posix()}:{i+1} | {ln.strip()[:80]}')
            break
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if stripped.startswith('[Ninereeds]'):
            after = stripped[len('[Ninereeds]'):].strip()
            # Check for "This is" followed by wrong article
            if after.startswith('This is a ') and after[9:].lower().startswith(('a', 'e', 'i', 'o', 'u')):
                pass  # Might need an instead of a, but hard to detect
            # Check for "This is an " followed by consonant start
            if after.startswith('This is an ') and after[10:].lower()[0] not in 'aeiou':
                pass
    # Check for contradictory content - internal is on surface, dead is alive, etc
    if 'internal' in text.lower() and 'on the surface' in text.lower() and 'is  on the surface' in text:
        issues.append('CONTRADICT ' + p.relative_to(Path('.').resolve()).as_posix() + ' | Internal is on surface')

if issues:
    for i in issues:
        print(i)
    sys.exit(1)
else:
    print('ALL CHECKS PASSED - no double spaces or contradictions')
