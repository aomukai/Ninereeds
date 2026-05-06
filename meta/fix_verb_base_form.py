"""
Fix 22 phase_3 verb files that still use base verb form (e.g., "Carve is...")
instead of gerund form (e.g., "Carving is...").

Converts base verb to gerund throughout, then applies orphan/Q2-with fixes.
Also fixes "when when" double-preposition in Q2 body lines.
"""

import re
from pathlib import Path

BASE_VERB_FILES = [
    ('phase_3/phase_3_219.md', 'carve'),
    ('phase_3/phase_3_220.md', 'improve'),
    ('phase_3/phase_3_223.md', 'slow'),
    ('phase_3/phase_3_226.md', 'fail'),
    ('phase_3/phase_3_228.md', 'develop'),
    ('phase_3/phase_3_229.md', 'resemble'),
    ('phase_3/phase_3_231.md', 'attach'),
    ('phase_3/phase_3_232.md', 'extend'),
    ('phase_3/phase_3_235.md', 'evolve'),
    ('phase_3/phase_3_250.md', 'engage'),
    ('phase_3/phase_3_252.md', 'sustain'),
    ('phase_3/phase_3_253.md', 'impair'),
    ('phase_3/phase_3_254.md', 'execute'),
    ('phase_3/phase_3_255.md', 'operate'),
    ('phase_3/phase_3_260.md', 'apply'),
    ('phase_3/phase_3_293.md', 'connect'),
    ('phase_3/phase_3_304.md', 'create'),
    ('phase_3/phase_3_308.md', 'crumble'),
    ('phase_3/phase_3_316.md', 'dangle'),
    ('phase_3/phase_3_319.md', 'decorate'),
    ('phase_3/phase_3_322.md', 'dine'),
    ('phase_3/phase_3_337.md', 'eat'),
]

Q2_MISSING_WITH = re.compile(r'^([A-Z][a-z]+ing happens )([a-z]+ and [a-z]+\.)$')


def to_gerund(verb):
    """Convert base verb to gerund form."""
    if verb.endswith('ie'):
        return verb[:-2] + 'ying'
    if verb.endswith('ing'):
        return verb  # already gerund
    # Ends in silent 'e' (not 'ee')
    if verb.endswith('e') and not verb.endswith('ee'):
        return verb[:-1] + 'ing'
    # Ends in 'y' preceded by vowel (e.g., play → playing)
    # Ends in 'y' preceded by consonant (e.g., apply → applying) - just add ing
    return verb + 'ing'


def fix_file(path, verb):
    text = path.read_text(encoding='utf-8-sig')
    gerund = to_gerund(verb)
    Verb = verb.capitalize()
    Gerund = gerund.capitalize()

    lines = text.splitlines()
    new_lines = []
    for line in lines:
        # Fix [user] question lines: base verb → gerund (lowercase)
        line = re.sub(
            r'(\[user\]what is )' + re.escape(verb) + r'(\?)',
            r'\g<1>' + gerund + r'\2', line
        )
        line = re.sub(
            r'(\[user\]when does )' + re.escape(verb) + r'( happen\?)',
            r'\g<1>' + gerund + r'\2', line
        )
        line = re.sub(
            r'(\[user\]what does )' + re.escape(verb) + r'( bring\?)',
            r'\g<1>' + gerund + r'\2', line
        )
        line = re.sub(
            r'(\[user\]what is )' + re.escape(verb) + r'( for\?)',
            r'\g<1>' + gerund + r'\2', line
        )

        # Fix [Ninereeds] and body lines: capitalized Verb → Gerund at line start
        if line.startswith('[Ninereeds]' + Verb + ' '):
            line = '[Ninereeds]' + Gerund + ' ' + line[len('[Ninereeds]' + Verb) + 1:]
        elif line.startswith(Verb + ' '):
            line = Gerund + ' ' + line[len(Verb) + 1:]

        # Fix "happens when when" → "happens when" (double-preposition artifact)
        line = re.sub(r'\bhappens when when\b', 'happens when', line)
        line = re.sub(r'\bhappens when in\b', 'happens in', line)
        line = re.sub(r'\bhappens when during\b', 'happens during', line)
        line = re.sub(r'\bhappens when on\b', 'happens on', line)

        # Fix Q2 missing-with summary
        m = Q2_MISSING_WITH.match(line)
        if m:
            line = m.group(1) + 'with ' + m.group(2)

        new_lines.append(line)

    ending = '\n' if text.endswith('\n') else ''
    path.write_text('\n'.join(new_lines) + ending, encoding='utf-8')
    print(f'  fixed: {path.parent.name}/{path.name} ({verb} -> {gerund})')


def main():
    repo = Path(__file__).parent.parent
    for rel_path, verb in BASE_VERB_FILES:
        path = repo / 'training_data/phases' / rel_path
        if not path.exists():
            print(f'  MISSING: {rel_path}')
            continue
        fix_file(path, verb)
    print(f'\nDone: {len(BASE_VERB_FILES)} files processed')


if __name__ == '__main__':
    main()
