#!/usr/bin/env python3
"""
Normalize vocab/phase_N_[pos]_new.txt files before backfill.
  1. Nouns: singularize using inflect
  2. Verbs: convert base form -> gerund (-ing)
  3. Adverbs: detect -ly forms in ANY list -> strip to base adjective, move to matching phase adj list
  4. Re-filter against vocab/taught_words.txt (drop already-taught)
  5. Deduplicate

Writes files in-place. Prints a change report to stdout.
"""

import re
import sys
from pathlib import Path
import inflect

REPO = Path(__file__).resolve().parents[2]
VOCAB = REPO / "vocab"
TAUGHT_FILE = VOCAB / "taught_words.txt"

p = inflect.engine()

# Noun endings that inflect incorrectly treats as English plurals (Latin/Greek or invariant)
_SAFE_SINGULAR_RE = re.compile(
    r'(us|is|ss|ous|ics|ness|ess|sis|rix|ies$)$|^(news|series|species|means|crossroads)$'
)


def safe_singularize(word):
    """Singularize word, but skip words ending in patterns inflect gets wrong."""
    if _SAFE_SINGULAR_RE.search(word.lower()):
        return word  # already singular, or invariant plural
    singular = p.singular_noun(word.lower())
    if singular and isinstance(singular, str) and len(singular) >= 3:
        return singular
    return word


# ----- Adjective base extraction for -ly adverbs -----
# These -ly words are adjectives (not adverbs) — do NOT strip them
_ADV_EXCEPTIONS = {
    "only", "early", "likely", "lonely", "lovely", "kindly", "elderly",
    "friendly", "lively", "silly", "holy", "ugly", "oily", "wobbly",
    "chilly", "woolly", "jolly", "burly", "curly", "gnarly",
    "daily", "weekly", "monthly", "yearly", "hourly",
    "apply", "imply", "reply", "rely", "supply", "multiply",
    "tally", "rally", "bully", "belly", "jelly", "holly", "dolly", "billy",
    # -ly adjectives that look like adverbs but are genuine adjectives:
    "smelly", "crinkly", "sparkly", "wiggly", "bubbly", "knobbly", "stubbly",
    "prickly", "crinkly", "wrinkly", "squiggly", "jiggly", "giggly", "niggly",
    "rubbly", "pebbly", "stubbly", "cobbbly", "wobbly", "knobby", "scrubbly",
    "orderly",  # "orderly" is an adjective meaning tidy/arranged
}

# Valid adjective-forming suffixes — only strip -ly when stem ends in one of these
_ADJ_STEM_SUFFIXES = (
    "al", "ous", "ful", "ent", "ant", "ive", "ic", "ect", "ete", "ate",
    "ish", "er", "en", "ire", "ure", "eal", "air", "ose", "ite",
)

# Words in noun/verb lists that are adverbs but not -ly derived
_KNOWN_ADVERBS = {
    "apart", "aside", "away", "together", "again", "ahead", "alone",
    "actually", "already", "also", "always", "anyway", "beyond",
    "ago", "soon", "still", "just", "else",
}


def adv_to_adj(word, taught=None):
    """
    If word is a -ly adverb, return its base adjective form.
    Return None if word is not an adverb (is an adjective or verb itself).
    """
    w = word.lower()
    if not w.endswith("ly"):
        if w in _KNOWN_ADVERBS:
            return w
        return None

    if w in _ADV_EXCEPTIONS:
        return None

    # -ily → -y (happily → happy, easily → easy)
    if w.endswith("ily"):
        return w[:-3] + "y"

    # -ably/-ibly → -able/-ible
    if w.endswith("ably"):
        return w[:-4] + "able"
    if w.endswith("ibly"):
        return w[:-4] + "ible"

    stem = w[:-2]
    if len(stem) < 4:
        return None  # too short to be a real adjective stem

    # Only accept if stem ends in a recognized adjective suffix
    if any(stem.endswith(s) for s in _ADJ_STEM_SUFFIXES):
        return stem

    # Also accept if stem is in taught_words (e.g. sharply → sharp)
    if taught and stem in taught:
        return stem

    # Otherwise: word is likely a true -ly adjective (sparkly, smelly, etc.)
    return None


# ----- Gerund formation -----
_VOWELS = set("aeiou")

# Explicit overrides: base verb → gerund
# Covers (1) base forms ending in -ing, (2) multi-syllable last-syllable-stress doublers,
# (3) c→ck rule (mimic, traffic), (4) British instal.
_GERUND_OVERRIDES = {
    # Base verbs ending in -ing (would be returned unchanged without override)
    "bring": "bringing", "cling": "clinging", "fling": "flinging",
    "ring": "ringing", "sing": "singing", "sling": "slinging",
    "spring": "springing", "sting": "stinging", "string": "stringing",
    "swing": "swinging", "wring": "wringing",
    # Multi-syllable verbs with last-syllable stress
    "admit": "admitting", "begin": "beginning", "commit": "committing",
    "compel": "compelling", "concur": "concurring", "confer": "conferring",
    "defer": "deferring", "embed": "embedding", "emit": "emitting",
    "equip": "equipping", "excel": "excelling", "expel": "expelling",
    "forget": "forgetting", "infer": "inferring", "input": "inputting",
    "occur": "occurring", "offset": "offsetting", "omit": "omitting",
    "output": "outputting", "permit": "permitting", "prefer": "preferring",
    "propel": "propelling", "quit": "quitting", "rebel": "rebelling",
    "refer": "referring", "regret": "regretting", "remit": "remitting",
    "repel": "repelling", "submit": "submitting", "transfer": "transferring",
    "underpin": "underpinning", "unplug": "unplugging", "unzip": "unzipping",
    "upset": "upsetting",
    # c → ck before -ing
    "frolic": "frolicking", "mimic": "mimicking", "panic": "panicking",
    "picnic": "picnicking", "traffic": "trafficking",
    # British spelling variant
    "instal": "installing",
}


def _vowel_groups(word):
    count, in_v = 0, False
    for c in word.lower():
        if c in _VOWELS:
            if not in_v:
                count += 1
                in_v = True
        else:
            in_v = False
    return count


def gerundize(word):
    w = word.lower().strip()
    if not w:
        return w
    if w in _GERUND_OVERRIDES:
        return _GERUND_OVERRIDES[w]
    if w.endswith("ing"):
        return w  # already a gerund
    if w.endswith("ie"):
        return w[:-2] + "ying"
    # Silent -e (not -ee, -oe, -ye); -ue verbs DO drop the e: argue→arguing
    if (w.endswith("e") and len(w) > 2
            and w[-2] not in _VOWELS
            and not w.endswith(("ee", "oe", "ye"))):
        return w[:-1] + "ing"
    # CVC doubling: only for single-syllable words
    if (len(w) >= 3
            and w[-1] not in "aeiouywxh"
            and w[-2] in _VOWELS
            and w[-3] not in _VOWELS
            and _vowel_groups(w) == 1):
        return w + w[-1] + "ing"
    return w + "ing"


# ----- Main -----

def load_taught():
    if TAUGHT_FILE.exists():
        return set(l.strip().lower() for l in TAUGHT_FILE.read_text().splitlines() if l.strip())
    return set()


def process_file(path, pos, phase, taught, adj_additions):
    """
    Read a word list, normalize, return cleaned list.
    adverbs found in noun/verb lists are appended to adj_additions[phase].
    """
    words = [l.strip().lower() for l in path.read_text().splitlines() if l.strip()]
    cleaned = []
    moved_to_adj = []
    changed = []

    for word in words:
        # --- adverb detection (noun and verb lists) ---
        if pos in ("nouns", "verbs"):
            adj_form = adv_to_adj(word, taught)
            if adj_form is not None:
                moved_to_adj.append((word, adj_form))
                adj_additions[phase].add(adj_form)
                continue  # remove from this list

        # --- noun singularization ---
        if pos == "nouns":
            singular = safe_singularize(word)
            if singular != word:
                changed.append((word, singular))
                word = singular

        # --- verb gerundization ---
        if pos == "verbs":
            gerund = gerundize(word)
            if gerund != word:
                changed.append((word, gerund))
                word = gerund

        # --- adjective adverb normalization (keep in adj list, normalize form) ---
        if pos == "adjectives":
            adj_form = adv_to_adj(word, taught)
            if adj_form is not None and adj_form != word:
                changed.append((word, adj_form))
                word = adj_form

        # --- filter out already-taught ---
        if word in taught:
            continue

        cleaned.append(word)

    # Dedup preserving first occurrence
    seen = set()
    deduped = []
    for w in cleaned:
        if w not in seen:
            seen.add(w)
            deduped.append(w)

    return deduped, changed, moved_to_adj


def main():
    taught = load_taught()
    print(f"Loaded {len(taught)} taught words.\n")

    # Collect cross-list adj additions keyed by phase
    adj_additions = {n: set() for n in range(1, 7)}

    # First pass: process nouns and verbs (collect adverb spillover)
    results = {}  # (phase, pos) -> (deduped, changed, moved)
    for phase in range(1, 7):
        for pos in ("nouns", "verbs"):
            fpath = VOCAB / f"phase_{phase}_{pos}_new.txt"
            if not fpath.exists():
                continue
            deduped, changed, moved = process_file(fpath, pos, phase, taught, adj_additions)
            results[(phase, pos)] = (deduped, changed, moved, fpath)

    # Second pass: process adjectives (also normalizes adverbs already there + adds moved ones)
    for phase in range(1, 7):
        fpath = VOCAB / f"phase_{phase}_adjectives_new.txt"
        pos = "adjectives"
        existing_words = []
        if fpath.exists():
            existing_words = [l.strip().lower() for l in fpath.read_text().splitlines() if l.strip()]
        # Merge in adverbs moved from noun/verb lists
        all_words = existing_words + sorted(adj_additions[phase])
        # Now normalize the combined list
        # Write to a temp list and process
        import tempfile, os
        tmp = Path(tempfile.mktemp())
        tmp.write_text("\n".join(all_words) + "\n" if all_words else "")
        deduped, changed, moved = process_file(tmp, pos, phase, taught, {n: set() for n in range(1,7)})
        tmp.unlink()
        results[(phase, pos)] = (deduped, changed, moved, fpath)

    # Write all files and report
    total_changed = 0
    total_removed = 0
    total_moved = 0
    for phase in range(1, 7):
        for pos in ("nouns", "verbs", "adjectives"):
            key = (phase, pos)
            if key not in results:
                continue
            deduped, changed, moved, fpath = results[key]
            orig_count = len(fpath.read_text().splitlines()) if fpath.exists() else 0
            new_count = len(deduped)
            removed = orig_count - new_count + len(moved)

            fpath.write_text("\n".join(deduped) + "\n" if deduped else "")

            if changed or moved or removed > 0:
                print(f"phase_{phase}_{pos}_new.txt: {orig_count} → {new_count} words")
                if changed:
                    sample = changed[:5]
                    more = f" (+{len(changed)-5} more)" if len(changed) > 5 else ""
                    print(f"  normalized: {', '.join(f'{a}→{b}' for a,b in sample)}{more}")
                if moved:
                    sample = moved[:5]
                    more = f" (+{len(moved)-5} more)" if len(moved) > 5 else ""
                    print(f"  → adj list: {', '.join(f'{a}→{b}' for a,b in sample)}{more}")
                if removed > len(moved):
                    print(f"  removed (taught): {removed - len(moved)}")
                total_changed += len(changed)
                total_moved += len(moved)

    print(f"\nSummary: {total_changed} forms normalized, {total_moved} adverbs moved to adj lists.")
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
