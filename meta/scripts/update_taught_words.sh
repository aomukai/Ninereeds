#!/bin/bash
# After each backfill batch: extract topic words from new phase files
# and append them to vocab/taught_words.txt.
# Usage: ./update_taught_words.sh

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
TAUGHT="$REPO/vocab/taught_words.txt"

python3 - "$REPO" "$TAUGHT" <<'EOF'
import re, sys
from pathlib import Path
from collections import Counter

REPO   = Path(sys.argv[1])
TAUGHT = Path(sys.argv[2])

VERB_PHRASES = r'(?:look like|do|give|mean|show|help|make|work|feel|sound|grow|move|live|come|go|appear|behave|change|tell|happen|occur|exist|form|develop|affect|involve|require|relate|represent|suggest|indicate|produce|cause|result|serve|function|begin|end|start|stop|become|stay|remain|seem|act|run|play|stand|fall|rise|flow|spread|shrink|connect|contain|include|allow|prevent|support|protect|create|express|describe|reflect|define)\b'
PATTERNS = [
    rf'^What do(?:es)? (?:the |a |an )?(.+?) {VERB_PHRASES}',
    r'^Where (?:can you find|does|do) (?:the |a |an )?(.+?)(?:\?|$)',
    r'^How does (?:the |a |an )?(.+?) ',
    r'^What is (?:a |an )?(.+?)$',
    r'^Why (?:does|is|are) (?:the |a |an )?(.+?) ',
    r'^When (?:does|is) (?:the |a |an )?(.+?) ',
    r'^What happens (?:in|to|during|with|when|at) (?:a |an |the )?(.+?)(?:\?|$)',
    r'^What do(?:es)? (?:the |a |an )?(\S+)',
]

def extract_topic(q):
    q = q.strip().rstrip('?')
    for pat in PATTERNS:
        m = re.match(pat, q, re.IGNORECASE)
        if m:
            return m.group(1).strip().lower()
    return None

existing = set(w.strip() for w in TAUGHT.read_text().splitlines() if w.strip())
new_words = set()

for f in sorted((REPO / 'training_data/phases').rglob('*.md')):
    questions = [l[len('[user]'):] for l in f.read_text().splitlines() if l.startswith('[user]')]
    candidates = [extract_topic(q) for q in questions if extract_topic(q)]
    if candidates:
        word = Counter(candidates).most_common(1)[0][0]
        if word not in existing:
            new_words.add(word)

if new_words:
    with TAUGHT.open('a') as fh:
        for w in sorted(new_words):
            fh.write(w + '\n')
    print(f"Added {len(new_words)} new words to taught_words.txt")
else:
    print("No new words found.")
EOF
