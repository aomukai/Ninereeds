"""
Scan all Format A phase files and flag those whose target word is not a noun.

Output: training_data/phases/POS_check.txt
  Each line: <filename>\t<word>\t<verdict>\t<pos_counts>

Verdict:
  NO_NOUN   — WordNet has zero noun synsets for this word (definite problem)
  NON_NOUN  — WordNet has some noun synsets but first (most common) is not noun
  SKIP      — word not in WordNet (compound phrase, proper noun, etc.)
  OK        — first synset is a noun
"""

import re
from pathlib import Path
from collections import Counter

import nltk
from nltk.corpus import wordnet as wn

nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)

OPENER_RE = re.compile(r'^\[Ninereeds\]This is (?:a |an |the )?(.+?)\.$', re.IGNORECASE)

def extract_target(text):
    """Return the target word/phrase from the first Format A opener found."""
    for line in text.splitlines():
        m = OPENER_RE.match(line.strip())
        if m:
            return m.group(1).strip().lower()
    return None

def pos_verdict(word):
    """
    Return (verdict, pos_counter_string) for the last significant word in `word`.
    For compound phrases like 'cup of water', check the head noun ('water').
    """
    # Use last word as head for compound phrases
    head = word.split()[-1].rstrip("s")   # rough depluralization

    synsets = wn.synsets(head)
    if not synsets:
        # Try original form
        synsets = wn.synsets(word.replace(" ", "_"))
    if not synsets:
        return "SKIP", ""

    pos_counts = Counter(s.pos() for s in synsets)
    pos_str = " ".join(f"{p}:{c}" for p, c in pos_counts.most_common())

    first_pos = synsets[0].pos()
    total = sum(pos_counts.values())
    noun_count = pos_counts.get("n", 0)

    if noun_count == 0:
        return "NO_NOUN", pos_str
    elif first_pos != "n":
        return "NON_NOUN", pos_str
    else:
        return "OK", pos_str

def main():
    repo = Path(__file__).parent.parent
    phase_dirs = sorted(repo.glob("training_data/phases/phase_*/"))

    flagged = []
    ok_count = 0
    skip_count = 0
    total = 0

    for phase_dir in phase_dirs:
        for path in sorted(phase_dir.glob("phase_*.md")):
            text = path.read_text(encoding="utf-8")

            # Skip Format B files (no "This is" opener)
            if "[Ninereeds]This is " not in text:
                continue

            total += 1
            word = extract_target(text)
            if not word:
                continue

            verdict, pos_str = pos_verdict(word)

            if verdict in ("NO_NOUN", "NON_NOUN"):
                flagged.append((path.parent.name + "/" + path.name, word, verdict, pos_str))
            elif verdict == "SKIP":
                skip_count += 1
            else:
                ok_count += 1

    out_path = repo / "training_data/phases/POS_check.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# POS check — {len(flagged)} flagged / {total} Format A files scanned\n")
        f.write(f"# Columns: filename | target_word | verdict | wordnet_pos_counts\n")
        f.write(f"# NO_NOUN = zero noun synsets; NON_NOUN = has noun synsets but not dominant\n\n")
        for filename, word, verdict, pos_str in flagged:
            f.write(f"{filename}\t{word}\t{verdict}\t{pos_str}\n")

    print(f"Scanned {total} Format A files")
    print(f"  OK:       {ok_count}")
    print(f"  SKIP:     {skip_count} (not in WordNet — compound phrases, proper nouns, etc.)")
    print(f"  Flagged:  {len(flagged)} (NO_NOUN + NON_NOUN)")
    print(f"    NO_NOUN:  {sum(1 for _,_,v,_ in flagged if v=='NO_NOUN')}")
    print(f"    NON_NOUN: {sum(1 for _,_,v,_ in flagged if v=='NON_NOUN')}")
    print(f"\nWritten to: {out_path}")

if __name__ == "__main__":
    main()
