import re
from pathlib import Path

BASE = Path.cwd()
issues = []
for p in sorted(Path('training_data/phases').rglob('phase_*.md')):
    try:
        rel = p.relative_to(BASE)
    except ValueError:
        rel = Path(*p.parts[-4:])
    text = p.read_text('utf-8')
    lines = text.strip().split('\n')
    
    # Check for blank line right after [Ninereeds]
    for i, ln in enumerate(lines):
        if ln.strip() == '[Ninereeds]' and i+1 < len(lines) and lines[i+1].strip() == '':
            issues.append(f'BLANK_OPENER {rel}:{i+1}')
            break
    
    # Check for === END ===
    if '=== END ===' in text:
        issues.append(f'ENDMARKER {rel}')
    
    # Check for stray fences
    if re.search(r'^```\s*$', text, re.MULTILINE):
        issues.append(f'FENCE {rel}')
    
    # Check block count
    user_count = text.count('[user]')
    nr_count = text.count('[Ninereeds]')
    if user_count != 4 or nr_count != 4:
        issues.append(f'BLOCK_COUNT {rel}: user={user_count} nr={nr_count}')
    
    # Check each Ninereeds answer for opener sentence structure
    nr_blocks = text.split('[Ninereeds]')
    for bi, block in enumerate(nr_blocks[1:], 1):
        body_lines = [l.strip() for l in block.split('\n') if l.strip() and not l.strip().startswith('[user]')]
        if not body_lines:
            continue
        opener = body_lines[0]
        if opener.count('.') != 1:
            issues.append(f'OPENER_SENTENCE {rel} block {bi}: {opener[:80]}')

if issues:
    print(f'Issues found: {len(issues)}')
    for i in issues[:50]:
        print(i)
    if len(issues) > 50:
        print(f'... and {len(issues)-50} more')
else:
    print('All phase files pass detailed validation')
