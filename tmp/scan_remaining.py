from pathlib import Path

queue_raw = Path('training_data/phases/repair_formatting.txt').read_text()
progress_raw = Path('training_data/phases/repair_progress_formatting.txt').read_text()

queue_lines = set()
for line in queue_raw.splitlines():
    if '.md' in line and '|' in line:
        parts = line.split('|', 1)
        queue_lines.add(parts[0].strip())

progress_lines = set()
for line in progress_raw.splitlines():
    line = line.strip()
    if '.md' in line:
        progress_lines.add(line)

remaining = sorted(queue_lines - progress_lines)
print(f'Queue unique: {len(queue_lines)}')
print(f'Progress unique: {len(progress_lines)}')
print(f'Remaining: {len(remaining)} files')
print()

for rel_path in remaining[:3]:
    print(f'Sample: {rel_path}')
    f = Path(rel_path)
    print(f'  Exists: {f.exists()}')
    print(f'  Abs: {f.absolute()}')

issues = []
for rel_path in remaining:
    f = Path(rel_path)
    if not f.exists():
        issues.append(f'{rel_path}: MISSING')
        continue
    content = f.read_text()
    lines = content.splitlines()
    if not lines:
        issues.append(f'{rel_path}: EMPTY')
        continue
    if lines[0].count('[user]') > 1:
        issues.append(f'{rel_path}: MULTIPLE [user] tags on line 1')
    if 'changes needed' in lines[0].lower() or 'prompt' in lines[0]:
        issues.append(f'{rel_path}: LEFTOVER COMMENTARY on line 1')
    if '[Ninereeds]' not in content:
        issues.append(f'{rel_path}: MISSING [Ninereeds] tags')

for i in issues:
    print(i)

print(f'\nFiles with issues: {len(issues)}')
if not issues:
    print('All remaining files appear structurally clean.')
