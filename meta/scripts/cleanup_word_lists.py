#!/usr/bin/env python3
"""
Targeted cleanup of vocab/phase_N_[pos]_new.txt files after bad normalization run.
Fixes:
  - Inflect-mangled nouns (fungu→fungus, iri→iris, etc.)
  - Bad adj strip results (crink→crinkly, sca→scaly, etc.)
  - Remove bad forms with no valid correction (junk, garbage)
  - Add back words that were silently lost (sparkly, orderly)
  - Remove junk: proper names, abbreviations, garbage strings
"""

from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[2]
VOCAB = REPO / "vocab"
TAUGHT_FILE = VOCAB / "taught_words.txt"


def load_taught():
    return set(l.strip().lower() for l in TAUGHT_FILE.read_text().splitlines() if l.strip())


# Explicit repairs: (file, bad_word, replacement_or_None)
# None = remove the word entirely
REPAIRS = {
    "phase_1_nouns_new.txt": [
        ("fungu", "fungus"),
        ("iri", "iris"),
        # Remove proper names and junk that crept in
        ("mae", None),
        ("mia", None),
        ("lee", None),
    ],
    "phase_2_nouns_new.txt": [
        ("addres", "address"),
        ("citru", "citrus"),
        # Abbreviations / garbage
        ("mr", None),
        ("m", None),
        ("pa", None),
        ("tv", None),
    ],
    "phase_3_nouns_new.txt": [
        ("basi", "basis"),
        ("focu", "focus"),
        ("versu", None),   # "versus" is a preposition, not a noun
        ("minu", None),    # "minus" is a preposition/conjunction
        ("plu", None),     # garbage
        ("multi", None),   # prefix fragment
        # Proper names
        ("jett", None),
        ("kai", None),
        ("kay", None),
        # Garbage/abbreviations
        ("wn", None),
        ("mof", None),
        ("los", None),
        ("mis", None),
        ("fus", None),
        # Words that are clearly verbs conjugated into the noun list
        # (these will still look odd but removing them risks losing real words;
        # leave "act", "age", "aid", "aim" — these are legit nouns)
    ],
    "phase_5_nouns_new.txt": [
        ("gu", None),      # truncated "gus" (proper name)
        ("ada", None),
        ("ava", None),
        ("bea", None),
        ("ben", None),
        ("eli", None),
        ("finn", None),
        ("gill", None),
        ("leo", None),
        ("ros", None),
        ("sam", None),
        ("scott", None),
        ("wyatt", None),
        ("zoe", None),
        ("jett", None),
        ("guy", None),
    ],
    "phase_6_nouns_new.txt": [
        ("minu", "minus"),  # minus as abstract noun is borderline but keep
        ("viru", "virus"),
        # Abbreviations / junk
        ("app", None),     # abbreviation — skip, too short/vague
        ("ca", None),
        ("cnt", None),
        ("ctr", None),
        ("dr", None),
        ("lc", None),
        ("lw", None),
        ("md", None),
        ("sy", None),
        ("arc", None),     # too short, ambiguous
    ],
    "phase_1_adjectives_new.txt": [
        # Bad strip results → restore original -ly adjective
        ("crink", "crinkly"),
        ("sca", "scaly"),
        ("smel", "smelly"),
        ("wigg", "wiggly"),
        # Add back lost word (sparkly → spark was in taught, so sparkly was silently removed)
        # handled by ADDITIONS below
    ],
    "phase_2_adjectives_new.txt": [
        ("bubb", "bubbly"),
        ("ful", None),     # "fully" → "full" is taught → remove
        ("citrus", None),  # citrus is a noun, not an adjective
    ],
    "phase_6_adjectives_new.txt": [
        ("tru", None),     # "truly" → "true" is taught → remove
    ],
    "phase_3_verbs_new.txt": [
        ("aliving", None),  # "alive" is adj, not a verb
    ],
}

# Words to add into specific files (recoveries + fixes)
ADDITIONS = {
    "phase_1_adjectives_new.txt": ["sparkly"],
    "phase_2_adjectives_new.txt": ["orderly"],
}

# Patterns for detecting obvious junk to remove (proper names, abbreviations)
_JUNK_PATTERNS = [
    re.compile(r'^[A-Z][a-z]+$'),   # Capitalized words (proper names) — shouldn't be in the files
    re.compile(r'^[a-z]{1,2}$'),    # 1-2 char fragments
    re.compile(r'^[A-Z]{2,}$'),     # ALL CAPS abbreviations
]

# Words that look like junk but are valid short words we want to keep
_KEEP_SHORT = {
    "a", "an", "the", "in", "on", "at", "up", "to", "of", "or",
    "big", "dim", "hot", "icy", "new", "old", "raw", "bad", "mad", "sad",
    "bud", "ivy", "pod", "cab", "pin", "soy", "air", "pee", "egg",
    "act", "age", "aid", "aim", "ask", "ate", "buy", "eat", "go", "got",
    "lay", "let", "put", "use", "run", "sit", "see", "get",
    "app",  # app is borderline but used in tech contexts
}


def is_junk(word):
    w = word.strip()
    if not w or w in _KEEP_SHORT:
        return False
    if len(w) <= 2 and w not in _KEEP_SHORT:
        return True
    # Patterns
    for pat in _JUNK_PATTERNS:
        if pat.match(w):
            return True
    return False


def repair_file(filename, taught):
    fpath = VOCAB / filename
    if not fpath.exists():
        return 0

    words = [l.strip().lower() for l in fpath.read_text().splitlines() if l.strip()]
    repairs = {bad: fix for bad, fix in REPAIRS.get(filename, [])}
    additions = [w for w in ADDITIONS.get(filename, []) if w not in taught]

    new_words = []
    changes = []
    for w in words:
        if w in repairs:
            fix = repairs[w]
            if fix is None:
                changes.append(f"  remove: {w}")
            else:
                changes.append(f"  fix: {w} → {fix}")
                if fix not in taught:
                    new_words.append(fix)
        elif is_junk(w):
            changes.append(f"  junk: {w}")
        else:
            new_words.append(w)

    # Add recovered words (avoid duplicates)
    existing_set = set(new_words)
    for w in additions:
        if w not in existing_set:
            new_words.append(w)
            changes.append(f"  add: {w}")
            existing_set.add(w)

    if changes:
        print(f"\n{filename} ({len(words)} → {len(new_words)}):")
        for c in changes:
            print(c)
        fpath.write_text("\n".join(new_words) + "\n")

    return len(changes)


def main():
    taught = load_taught()
    total = 0
    for filename in sorted(set(list(REPAIRS.keys()) + list(ADDITIONS.keys()))):
        total += repair_file(filename, taught)

    print(f"\nTotal: {total} changes.")

    print("\nFinal counts:")
    for phase in range(1, 7):
        parts = []
        for pos in ("nouns", "verbs", "adjectives"):
            fpath = VOCAB / f"phase_{phase}_{pos}_new.txt"
            if fpath.exists():
                n = len([l for l in fpath.read_text().splitlines() if l.strip()])
                parts.append(f"{pos[:3]}:{n}")
        print(f"  phase_{phase}: {', '.join(parts)}")


if __name__ == "__main__":
    main()
