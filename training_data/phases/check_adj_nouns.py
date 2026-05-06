#!/usr/bin/env python3
"""
Check subjects used in adj_rewrites.md against allowed_nouns.txt.
Reports any subject noun not covered by the allowlist.
"""

import re
from pathlib import Path
from collections import defaultdict

PHASES_DIR = Path(__file__).parent
REWRITES_FILE = PHASES_DIR / "adj_rewrites.md"
QUEUE_FILE    = PHASES_DIR / "adj_rewrite_queue.txt"
ALLOWED_FILE  = PHASES_DIR / "allowed_nouns.txt"

# ── load allowed nouns ────────────────────────────────────────────────────────
allowed = set()
with open(ALLOWED_FILE) as f:
    for line in f:
        word = line.strip().split("\t")[0].lower()
        if word:
            allowed.add(word)

# ── load queue: word → filename (first occurrence wins) ──────────────────────
word_to_file = {}
with open(QUEUE_FILE) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            filepath, word = parts[0].strip(), parts[1].strip().lower()
            if word not in word_to_file:
                word_to_file[word] = filepath

# ── parse adj_rewrites.md into (word, pos_line, neg_line) blocks ──────────────
def parse_blocks(path):
    with open(path) as f:
        lines = [l.rstrip() for l in f]
    i = 0
    while i < len(lines):
        if not lines[i]:
            i += 1
            continue
        m = re.match(r'\[user\]What does (.+?) mean\?', lines[i], re.IGNORECASE)
        if not m:
            i += 1
            continue
        word = m.group(1).lower()
        if i + 3 < len(lines) and lines[i + 1].startswith("[Ninereeds]"):
            yield word, lines[i + 2], lines[i + 3]
            i += 4
        else:
            i += 1

# ── subject extraction ────────────────────────────────────────────────────────
def extract_subject(sentence):
    """Pull the subject NP from '[subject] is [not] [adj].'"""
    s = sentence.strip().rstrip(".")
    s = re.sub(r'\s+(?:is|are)\s+not\s+.*$', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\s+(?:is|are)\s+.*$',      '', s, flags=re.IGNORECASE)
    s = s.strip().lower()
    s = re.sub(r'^(?:a|an|the)\s+', '', s)
    return s or None

def in_allowed(subject):
    """True if any word in the subject phrase is in the allowlist."""
    if subject in allowed:
        return True
    for word in subject.split():
        if word.rstrip(".,;:") in allowed:
            return True
    return False

# ── main check ────────────────────────────────────────────────────────────────
missing = defaultdict(list)   # subject → [(adj_word, filename)]
total_blocks = 0

for adj_word, pos_line, neg_line in parse_blocks(REWRITES_FILE):
    total_blocks += 1
    filename = word_to_file.get(adj_word, "?")
    for line in (pos_line, neg_line):
        for sentence in re.split(r'(?<=\.)\s+', line.strip()):
            if not sentence.strip():
                continue
            subj = extract_subject(sentence)
            if subj and not in_allowed(subj):
                missing[subj].append((adj_word, filename))

# ── report ────────────────────────────────────────────────────────────────────
print(f"Blocks checked : {total_blocks}")
print(f"Allowed nouns  : {len(allowed)}")
print(f"Unknown subjects: {len(missing)}")
print()

for subj in sorted(missing.keys()):
    entries = missing[subj]
    adj_list = ", ".join(w for w, _ in entries)
    print(f"  {subj:<35} → {adj_list}")
