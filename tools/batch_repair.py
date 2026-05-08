"""Batch repair phase files: formatting fixes + structural/duplicate fixes."""

import re
import os
import sys

REPAIR_LOG = "meta/repair_run2.log"

def read_lines(path):
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]

def write_lines(path, lines):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for line in lines:
            f.write(line + "\n")

def fix_q2_template(line):
    s = line.strip()
    lower = s.lower()
    if lower.startswith('[user]where is ') and 'where can you find' not in lower and 'where does' not in lower:
        # Handle "Where is X found?" and "Where is X?"
        rest = s[len('[user]where is '):]
        if rest.lower().endswith(' found?'):
            rest = rest[:-len(' found?')].strip() + '?'
        lead = '[user]' if s.startswith('[user]') else '[user]'
        if s[len(lead):][0].islower():
            return f'[user]where can you find {rest}'
        else:
            return f'[user]Where can you find {rest}'
    return line

def fix_q4_template(line):
    s = line.strip()
    lower = s.lower()
    if lower.startswith('[user]') and (' for?' in lower):
        # Patterns: "what is X for?", "what is X used for?", "what are X for?"
        lead = '[user]' if s.startswith('[user]') else '[user]'
        rest = s[len(lead):]
        rest_lower = rest.lower()
        
        if rest_lower.startswith('what is ') and ' used for?' in rest_lower:
            # "What is X used for?" -> "What does X give?"
            subject = rest[len('what is '):-len(' used for?')].strip()
            verb = 'does'
        elif rest_lower.startswith('what is ') and rest_lower.endswith(' for?'):
            # "What is X for?" -> "What does X give?"
            subject = rest[len('what is '):-len(' for?')].strip()
            verb = 'does'
        elif rest_lower.startswith('what are ') and rest_lower.endswith(' for?'):
            # "What are X for?" -> "What do X give?"
            subject = rest[len('what are '):-len(' for?')].strip()
            verb = 'do'
        else:
            return line
        
        if rest[0].islower():
            return f'{lead}what {verb} {subject} give?'
        else:
            return f'{lead}What {verb} {subject} give?'
    return line

def remove_negation(text):
    """Remove negation words from body lines, but keep definitional uses."""
    s = text.strip()
    # Don't process if it's a [user] line
    if s.startswith('[user]'):
        return text
    
    lower = s.lower()
    
    # Remove standalone "not" (but not "without" or "nothing" etc.)
    if ' not ' in lower:
        s = re.sub(r'\bnot\b', '', s, flags=re.IGNORECASE)
        s = re.sub(r'  +', ' ', s).strip()
    
    # Handle "no X" -> convert to affirmative
    if ' no ' in lower:
        # Replace "has no" / "have no" / "with no" with "lacks" 
        s = re.sub(r'\bhas no\b', 'lacks', s, flags=re.IGNORECASE)
        s = re.sub(r'\bhave no\b', 'lack', s, flags=re.IGNORECASE)
        s = re.sub(r'\bwith no\b', 'without', s, flags=re.IGNORECASE)
        s = re.sub(r'\bmeans no\b', 'lacks', s, flags=re.IGNORECASE)
        s = re.sub(r'\bgives no\b', 'lacks', s, flags=re.IGNORECASE)
        s = re.sub(r'\boffers no\b', 'lacks', s, flags=re.IGNORECASE)
        # Catch remaining "no X" where possible
        s = re.sub(r'\bno\b ', '', s, flags=re.IGNORECASE)
        s = re.sub(r'  +', ' ', s).strip()
    
    return s

def fix_file_all(path):
    lines = read_lines(path)
    changed = False
    new_lines = []
    for line in lines:
        stripped = line.rstrip('\n')
        original = stripped

        if stripped.startswith('[user]'):
            stripped = fix_q2_template(stripped)
            stripped = fix_q4_template(stripped)

        if stripped.startswith('[Ninereeds]'):
            body = stripped[len('[Ninereeds]'):]
            if body:
                fixed_body = remove_negation(body)
                if fixed_body != body:
                    stripped = '[Ninereeds]' + fixed_body
        elif not stripped.startswith('[') and stripped:
            stripped = remove_negation(stripped)

        new_lines.append(stripped)

    # Fix summary "or" -> "and" at the four summary positions
    for idx in [7, 16, 25, 34]:
        if idx < len(new_lines):
            line = new_lines[idx]
            s = line.strip()
            if s and not s.startswith('[') and ' and ' not in s and ' or ' in s:
                new_lines[idx] = s.replace(' or ', ' and ')

    if new_lines != lines:
        write_lines(path, new_lines)
        return True
    return False

def check_needs_repair(path):
    lines = read_lines(path)
    issues = {}
    if len(lines) != 35:
        issues['line_count'] = len(lines)
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('[user]'):
            lower = stripped.lower()
            if 'where is ' in lower and 'where can you find' not in lower and 'where does' not in lower:
                issues.setdefault('q2_template', []).append(i)
            if ('what is ' in lower or 'what are ' in lower) and (' for?' in lower or ' used for?' in lower):
                issues.setdefault('q4_template', []).append(i)
        elif stripped.startswith('[Ninereeds]') or not stripped.startswith('['):
            for nw in [' not ', ' no ', ' never ', ' without ']:
                if nw in stripped.lower():
                    issues.setdefault('negation', []).append((i, nw.strip()))
    for idx in [8, 17, 26, 35]:
        if idx <= len(lines):
            l = lines[idx-1].strip()
            if l and not l.startswith('[') and ' and ' not in l:
                issues.setdefault('summary_no_and', []).append(idx)
    return issues if issues else None


def main():
    os.makedirs(os.path.dirname(REPAIR_LOG), exist_ok=True)
    report_lines = []

    step = sys.argv[1] if len(sys.argv) > 1 else 'formatting'

    if step == 'formatting':
        with open('training_data/phases/repair_progress_formatting.txt') as f:
            seen = set()
            formatting_files = []
            for l in f:
                l = l.strip()
                if l and l not in seen:
                    seen.add(l)
                    formatting_files.append(l)

        report_lines.append(f"Formatting queue: {len(formatting_files)} unique files")

        fixed = 0
        already_clean = 0
        errors = []

        for fpath in formatting_files:
            if not os.path.exists(fpath):
                errors.append(f"NOT FOUND: {fpath}")
                continue
            issues = check_needs_repair(fpath)
            if not issues:
                already_clean += 1
            else:
                try:
                    if fix_file_all(fpath):
                        fixed += 1
                    else:
                        already_clean += 1
                except Exception as e:
                    errors.append(f"ERROR fixing {fpath}: {e}")

        report_lines.append(f"Fixed: {fixed}, Already clean: {already_clean}, Errors: {len(errors)}")
        for e in errors:
            report_lines.append(f"  {e}")

        # Verify ALL
        still_broken = 0
        broken_summary = {'q2':0, 'q4':0, 'neg':0, 'lines':0, 'summary_and':0}
        for fpath in formatting_files:
            if os.path.exists(fpath):
                issues = check_needs_repair(fpath)
                if issues:
                    still_broken += 1
                    if 'q2_template' in issues: broken_summary['q2'] += 1
                    if 'q4_template' in issues: broken_summary['q4'] += 1
                    if 'negation' in issues: broken_summary['neg'] += 1
                    if 'line_count' in issues: broken_summary['lines'] += 1
                    if 'summary_no_and' in issues: broken_summary['summary_and'] += 1

        report_lines.append(f"Post-fix verify: {still_broken} still broken out of {len(formatting_files)}")
        report_lines.append(f"  Q2: {broken_summary['q2']}, Q4: {broken_summary['q4']}, Neg: {broken_summary['neg']}, Lines: {broken_summary['lines']}, Sum&: {broken_summary['summary_and']}")

    elif step == 'structural':
        dupe_files = [l.strip() for l in read_lines('training_data/phases/repair_progress_duplicate.txt') if l.strip()]
        report_lines.append(f"Structural/duplicate queue: {len(dupe_files)} files")

        repaired = 0
        needs_regen = []
        errors = []

        for fpath in dupe_files:
            if not os.path.exists(fpath):
                errors.append(f"NOT FOUND: {fpath}")
                continue

            lines = read_lines(fpath)
            nlines = len(lines)
            user_count = sum(1 for l in lines if l.strip().startswith('[user]'))
            nr_count = sum(1 for l in lines if l.strip().startswith('[Ninereeds]'))

            if nlines < 20 or user_count < 4 or nr_count < 4:
                needs_regen.append(fpath)
                report_lines.append(f"  NEEDS REGEN: {fpath} ({nlines} lines, {user_count} user, {nr_count} ninereeds)")
            else:
                try:
                    if fix_file_all(fpath):
                        repaired += 1
                except Exception as e:
                    errors.append(f"ERROR repairing {fpath}: {e}")

        report_lines.append(f"Repaired: {repaired}, Needs regen: {len(needs_regen)}, Errors: {len(errors)}")

    with open(REPAIR_LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")
    print("\n".join(report_lines))


if __name__ == "__main__":
    main()
