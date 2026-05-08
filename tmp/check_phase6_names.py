from pathlib import Path
import re
p6 = Path('training_data/phases/phase_6')
for f in sorted(p6.glob('*.md')):
    name = f.name
    if not name.startswith('phase_6_') and name != 'adj_rewrites.md':
        text = f.read_text(encoding='utf-8')
        lines = text.splitlines()
        uc = text.count('[user]')
        nc = text.count('[Ninereeds]')
        has_end = '=== END ===' in text
        bl = any(lines[i].strip() == '[Ninereeds]' and i+1 < len(lines) and not lines[i+1].strip() for i in range(len(lines)))
        print(f'{name}: {len(lines)} lines, user={uc}, ninereeds={nc}, end={has_end}, blank_opener={bl}')
