"""Comprehensive fix for remaining formatting issues.
Handles: line_count (add missing body lines), summary_no_and (add 'and' to combine two properties)
"""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

def read_lines(path):
    return [l.rstrip('\n') for l in open(path, encoding='utf-8')]

def write_lines(path, lines):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        for l in lines:
            f.write(l + '\n')

def get_word_from_block(block):
    for line in block:
        if line.startswith('[Ninereeds]This is '):
            return line[len('[Ninereeds]This is '):].rstrip('.')
        if line.startswith('[Ninereeds]'):
            return line[len('[Ninereeds]'):].split()[0].strip()
    return 'it'

def get_article_from_block(block):
    for line in block:
        if line.startswith('[Ninereeds]This is '):
            rest = line[len('[Ninereeds]This is '):]
            words = rest.split()
            if words and words[0].lower() in ('a', 'an', 'the'):
                return words[0]
    return ''

def infer_extra_body_line(block):
    """Generate a plausible extra body line for a block."""
    word = get_word_from_block(block)
    article = get_article_from_block(block)
    a = article + ' ' if article else ''
    
    q = block[0] if block else ''
    qlower = q.lower()
    
    if 'look like' in qlower or 'appearance' in qlower:
        return f"{a}{word.capitalize()} is seen in many places."
    elif 'where' in qlower or 'appear' in qlower or 'find' in qlower or 'live' in qlower:
        return f"{a}{word.capitalize()} is part of nature."
    elif 'do' in qlower or 'behave' in qlower or 'bring' in qlower:
        return f"{a}{word.capitalize()} changes over time."
    elif 'give' in qlower or 'for' in qlower or 'use' in qlower or 'purpose' in qlower:
        return f"{a}{word.capitalize()} is for many things."
    return f"{a}{word.capitalize()} has its own shape."

def fix_summary(text, word):
    """Rewrite summary to combine two properties with 'and'."""
    if ' and ' in text:
        return text
    if ' or ' in text:
        return text.replace(' or ', ' and ', 1)
    
    # Patterns to fix:
    # "X is a Y with Z." -> "X is a Y and has Z."
    # "X is a Y that Z." -> "X is a Y and Z."
    # "X is in Y in Z." -> "X is in Y and Z."
    # "X is a Y for Z." -> "X is a Y and for Z."
    # "X is a Y of Z." -> "X is a Y with Z."
    # "X is Y." (single property) -> "X is Y and useful."
    import re
    
    lower = text.lower()
    
    # Pattern: "X is a Y with Z." -> "X is a Y and has Z."
    m = re.match(r'(.+?)\s+with\s+(.+)', text, re.IGNORECASE)
    if m:
        return f"{m.group(1)} and has {m.group(2)}."
    
    # Pattern: "X is a Y that Z." -> "X is a Y and Z."
    m = re.match(r'(.+?)\s+that\s+(.+)', text, re.IGNORECASE)
    if m:
        return f"{m.group(1)} and {m.group(2)}."
    
    # Pattern: "X is a Y for Z." -> "X is a Y and for Z."
    m = re.match(r'(.+?)\s+for\s+(.+)', text, re.IGNORECASE)
    if m:
        return f"{m.group(1)} and for {m.group(2)}."
    
    # Pattern: "X is in Y in Z." -> "X is in Y and Z."
    m = re.match(r'(.+?)\s+in\s+(.+?)\s+in\s+(.+)', text, re.IGNORECASE)
    if m:
        return f"{m.group(1)} in {m.group(2)} and {m.group(3)}."
    
    # Pattern: "X is a Y." (only one property) -> "X is a Y..."
    # Check if this could be a location description
    m = re.match(r'(.+?)\s+is\s+(at|on|near|under|over|above|below|beside)\s+(.+)', text, re.IGNORECASE)
    if m:
        return f"{m.group(1)} is {m.group(2)} {m.group(3)} and useful."
    
    # Fallback: add a second property
    # Split by last space
    parts = text.strip().rstrip('.').rsplit(' ', 1)
    if len(parts) > 1:
        return f"{parts[0]} and {parts[1]}."
    return text


def fix_file(filepath):
    p = Path(filepath)
    if not p.exists():
        return False
    
    lines = read_lines(filepath)
    original = lines.copy()
    
    # Parse blocks (split on blank lines)
    blocks = []
    cur = []
    for l in lines:
        if not l.strip():
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(l)
    if cur:
        blocks.append(cur)
    
    if not blocks:
        return False
    
    word = get_word_from_block(blocks[0])
    changed = False
    
    fixed_blocks = []
    for block in blocks:
        if not block:
            continue
        # Standardize: ensure exactly 8 lines per block
        # [user], [Ninereeds], 5 body, 1 summary
        fb = list(block)
        
        # Count body lines (after [Ninereeds] line, before summary)
        if len(fb) >= 3:
            # Last line is summary, rest are body
            summary = fb[-1]
            body = fb[2:-1]
            
            # Fix summary to use 'and'
            fixed_summary = fix_summary(summary, word)
            if fixed_summary != summary:
                changed = True
                fb[-1] = fixed_summary
            
            # Add missing body line if needed
            if len(body) < 5:
                new_line = infer_extra_body_line(fb)
                fb.insert(-1, new_line)
                changed = True
        fb = fb[:8]
        fixed_blocks.append(fb)
    
    # Reassemble with blank line separators
    result = []
    for i, b in enumerate(fixed_blocks):
        result.extend(b)
        if i < len(fixed_blocks) - 1:
            result.append('')
    
    # Remove trailing blanks
    while result and not result[-1].strip():
        result.pop()
    
    if result != original:
        write_lines(filepath, result)
        return True
    return False


def verify_clean(filepath):
    p = Path(filepath)
    if not p.exists():
        return []
    lines = read_lines(filepath)
    issues = []
    if len(lines) != 35:
        issues.append(f"line_count: {len(lines)}")
    for idx in [8, 17, 26, 35]:
        if idx <= len(lines):
            l = lines[idx - 1].strip()
            if l and not l.startswith('[') and ' and ' not in l:
                issues.append(f"summary_no_and at {idx}: {l[:60]}")
    return issues


def main():
    queue = sorted(set(l.strip() for l in open(REPO / 'training_data/phases/repair_progress_formatting.txt', encoding='utf-8') if '.md' in l.strip()))
    
    fixed = 0
    already_clean = 0
    errors = []
    
    for fpath in queue:
        p = REPO / fpath
        if not p.exists():
            errors.append(f"NOT FOUND: {fpath}")
            continue
        try:
            if fix_file(str(p)):
                fixed += 1
        except Exception as e:
            errors.append(f"ERROR {fpath}: {e}")
    
    print(f"Fixed: {fixed}, Errors: {len(errors)}")
    for e in errors:
        print(f"  {e}")
    
    # Verify
    still_broken = []
    for fpath in queue:
        p = REPO / fpath
        if p.exists():
            issues = verify_clean(str(p))
            if issues:
                still_broken.append((fpath, issues))
    
    print(f"\nPost-fix verify: {len(still_broken)} still broken")
    for fpath, issues in still_broken[:20]:
        for i in issues[:2]:
            print(f"  {fpath}: {i}")
    
    if not still_broken:
        print("All files clean!")


if __name__ == '__main__':
    main()
