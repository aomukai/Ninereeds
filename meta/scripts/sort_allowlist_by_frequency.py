#!/usr/bin/env python3
"""
Sort training_data/allowlist.txt by English corpus frequency (most common first).
Uses the wordfreq library. Multi-word entries (e.g. "blade of grass") are scored
as phrases; hyphenated or unknown forms fall back to 0.0 and land at the bottom.
"""

import sys
from pathlib import Path

try:
    from wordfreq import zipf_frequency
except ImportError:
    print("wordfreq not installed. Run: pip install wordfreq", file=sys.stderr)
    sys.exit(1)

ALLOWLIST = Path(__file__).parent.parent.parent / "training_data" / "allowlist.txt"


def score(word: str) -> float:
    # zipf_frequency returns 0.0 for unknowns; that's fine — they sink to the bottom
    return zipf_frequency(word, "en")


def main():
    words = [w for w in ALLOWLIST.read_text(encoding="utf-8").splitlines() if w.strip()]
    words.sort(key=score, reverse=True)
    ALLOWLIST.write_text("\n".join(words) + "\n", encoding="utf-8")
    print(f"Sorted {len(words)} entries. Top 10:")
    for w in words[:10]:
        print(f"  {score(w):.2f}  {w}")
    print("  ...")
    print(f"Bottom 5 (score 0 = unknown to wordfreq):")
    for w in words[-5:]:
        print(f"  {score(w):.2f}  {w}")


if __name__ == "__main__":
    main()
