"""
From POS_check.txt, extract entries where the target word is primarily a verb.
Writes training_data/phases/verbs.txt.

Also writes adjectives.txt and adverbs.txt for later review.
"""

from pathlib import Path
from collections import Counter
import nltk
from nltk.corpus import wordnet as wn

nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)

def dominant_pos(word):
    """
    Return the dominant WordNet POS for a word:
      'v' = verb, 'n' = noun, 'a'/'s' = adjective, 'r' = adverb, '?' = unknown
    'dominant' = POS of the first synset (most common sense per WordNet ordering).
    """
    # For compounds / phrases use the head word (last token)
    head = word.split()[-1]

    synsets = wn.synsets(head)
    if not synsets:
        synsets = wn.synsets(word.replace(" ", "_"))
    if not synsets:
        return "?"

    return synsets[0].pos()   # first synset = most common sense

def pos_group(pos):
    """Map WordNet pos codes to broad groups."""
    return {
        'v': 'verb',
        'n': 'noun',
        'a': 'adj',
        's': 'adj',
        'r': 'adv',
    }.get(pos, 'other')

def main():
    repo = Path(__file__).parent.parent
    check_file = repo / "training_data/phases/POS_check.txt"

    buckets = {"verb": [], "adj": [], "adv": [], "noun": [], "other": []}

    with open(check_file, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            filename, word, verdict = parts[0], parts[1], parts[2]
            pos = dominant_pos(word)
            group = pos_group(pos)
            buckets[group].append((filename, word))

    out_dir = repo / "training_data/phases"

    for group, entries in buckets.items():
        if not entries:
            continue
        out_path = out_dir / f"{group}s.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(f"# {group.upper()}S — {len(entries)} files\n")
            f.write(f"# Columns: filename | word\n\n")
            for filename, word in sorted(entries):
                f.write(f"{filename}\t{word}\n")
        print(f"{group:8s}: {len(entries):3d} files -> {out_path.name}")

    print(f"\nTotal flagged: {sum(len(v) for v in buckets.values())}")

if __name__ == "__main__":
    main()
