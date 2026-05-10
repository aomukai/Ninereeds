"""
Verify tier-1 triplet stories against the allowlist.
Usage:
  python3 verify_t1_stories.py              # check all files in tmp/triplet_t1_output/
  python3 verify_t1_stories.py path/to/file.md ...

Reports per-file: PASS / FAIL with flagged words.
Writes summary to tmp/triplet_t1_violations.txt
"""

import os
import re
import sys

REPO = "/home/aomukai/Ninereeds"
ALLOWLIST_PATH = f"{REPO}/tmp/allowlist_full.txt"
STORY_DIR = f"{REPO}/tmp/triplet_t1_output"
VIOLATIONS_OUT = f"{REPO}/tmp/triplet_t1_violations.txt"

# ── Load allowlist ─────────────────────────────────────────────────────────────

with open(ALLOWLIST_PATH) as f:
    ALLOWLIST = set(w.strip().lower() for w in f if w.strip())

# Common function words / grammatical words not in the content allowlist but always valid.
# Function words are inferrable from patterns; the allowlist only gates content words.
FUNCTION_WORDS = {
    "also", "these", "those", "such", "both", "each", "every", "any", "all",
    "some", "few", "many", "more", "most", "less", "least", "much", "enough",
    "either", "neither", "other", "another", "same", "different", "own",
    "very", "quite", "rather", "almost", "already", "always", "never",
    "often", "sometimes", "usually", "again", "still", "yet", "just",
    "only", "even", "too", "also", "instead", "however", "therefore",
    "because", "although", "unless", "until", "while", "since", "after",
    "before", "when", "where", "which", "that", "what", "who", "whose",
    "whom", "how", "why", "whether", "if", "then", "than", "as",
    "this", "here", "there", "now", "then", "so", "but", "and", "or",
    "nor", "not", "no", "yes", "well", "oh", "upon", "within", "without",
    "between", "among", "through", "during", "against", "toward", "towards",
    "across", "along", "around", "behind", "below", "beneath", "beside",
    "beyond", "except", "inside", "outside", "since", "throughout", "under",
    "underneath", "until", "upon", "via", "whereas", "whereby",
}

# ── Inflection helpers ─────────────────────────────────────────────────────────
# Simple suffix-stripping: accept a word if any stripped form is on the allowlist.
# This handles common English morphology without a full lemmatizer.

STRIP_SUFFIXES = [
    "iest", "ier",           # superlative / comparative of -y adjectives
    "ness",                  # brightness, softness
    "ment",                  # movement
    "tion", "sion",          # rotation, expansion
    "ling", "ting", "ning",  # doubling consonant + ing: running, sitting
    "ying",                  # flying → fl + ying… handled below
    "ing",                   # walking, jumping
    "ied",                   # tried, carried
    "ied",
    "ier",
    "est",                   # coldest
    "er",                    # colder, walker
    "ly",                    # slowly, brightly
    "ed",                    # walked
    "es",                    # boxes, goes
    "s",                     # runs, dogs
    "en",                    # broken → broke? (imperfect but catches some)
]

def allowed(word):
    w = word.lower().strip(".,!?;:\"'()-—")
    if not w or w.isdigit():
        return True
    if w in FUNCTION_WORDS:
        return True
    # Strip possessive 's
    if w.endswith("'s"):
        w = w[:-2]
    elif w.endswith("s'"):
        w = w[:-1]
    if not w:
        return True
    if w in ALLOWLIST:
        return True
    # Try removing suffixes and check base
    for sfx in STRIP_SUFFIXES:
        if w.endswith(sfx) and len(w) - len(sfx) >= 2:
            base = w[: -len(sfx)]
            if base in ALLOWLIST:
                return True
            # silent-e before suffix: smiled→smile, agreed→agree, wobbled→wobble
            if base + "e" in ALLOWLIST:
                return True
            # doubled final consonant (running → run, sitting → sit)
            if len(base) >= 2 and base[-1] == base[-2]:
                if base[:-1] in ALLOWLIST:
                    return True
            # -ying case: flying → fly
            if sfx == "ing" and w.endswith("ying"):
                fly_base = w[:-4] + "y"
                if fly_base in ALLOWLIST:
                    return True
    # -ied case: tried → try, carried → carry
    if w.endswith("ied"):
        y_base = w[:-3] + "y"
        if y_base in ALLOWLIST:
            return True
    # common irregular past tense → base form lookup
    IRREGULAR = {
        "drew": "draw", "drove": "drive", "fell": "fall", "fought": "fight",
        "flew": "fly", "froze": "freeze", "gave": "give", "grew": "grow",
        "held": "hold", "hid": "hide", "hung": "hang", "knew": "know",
        "laid": "lay", "led": "lead", "left": "leave", "lit": "light",
        "meant": "mean", "met": "meet", "paid": "pay", "rode": "ride",
        "rang": "ring", "rose": "rise", "ran": "run", "said": "say",
        "sang": "sing", "sank": "sink", "sat": "sit", "slept": "sleep",
        "slid": "slide", "smelt": "smell", "spoke": "speak", "spent": "spend",
        "stood": "stand", "stole": "steal", "swam": "swim", "swept": "sweep",
        "swung": "swing", "took": "take", "taught": "teach", "tore": "tear",
        "threw": "throw", "woke": "wake", "wore": "wear", "won": "win",
        "wrote": "write", "broke": "break", "brought": "bring",
        "built": "build", "bought": "buy", "caught": "catch", "chose": "choose",
        "came": "come", "cut": "cut", "dug": "dig", "found": "find",
        "got": "get", "heard": "hear", "hit": "hit", "hurt": "hurt",
        "kept": "keep", "let": "let", "lost": "lose", "made": "make",
        "put": "put", "read": "read", "set": "set", "shot": "shoot",
        "shown": "show", "shut": "shut", "sent": "send", "seen": "see",
        "sold": "sell", "told": "tell", "thought": "think", "understood": "understand",
    }
    if w in IRREGULAR and IRREGULAR[w] in ALLOWLIST:
        return True
    return False


# ── Story extraction ───────────────────────────────────────────────────────────

def extract_story_words(path):
    """Return list of (word, line_number) from the [Ninereeds] block."""
    words = []
    in_story = False
    with open(path) as f:
        for lineno, line in enumerate(f, 1):
            stripped = line.strip()
            if stripped.startswith("[Ninereeds]"):
                in_story = True
                text = stripped[len("[Ninereeds]"):]
            elif stripped.startswith("[user]"):
                in_story = False
                continue
            elif in_story:
                text = stripped
            else:
                continue
            for tok in re.split(r"[\s\-]+", text):
                clean = tok.lower().strip(".,!?;:\"'()—")
                if clean:
                    words.append((clean, lineno))
    return words


# ── Checks ─────────────────────────────────────────────────────────────────────

def check_file(path):
    issues = []

    if not os.path.exists(path):
        return [f"FILE MISSING: {path}"]

    with open(path) as f:
        content = f.read()

    # Must have [user] and [Ninereeds] blocks
    if "[user]" not in content:
        issues.append("Missing [user] line")
    if "[Ninereeds]" not in content:
        issues.append("Missing [Ninereeds] block")

    # Sentence count (rough: split on ". " or ".\n")
    ninereeds_block = re.search(r"\[Ninereeds\](.*)", content, re.DOTALL)
    if ninereeds_block:
        story_text = ninereeds_block.group(1).strip()
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", story_text) if s.strip()]
        if len(sentences) < 6:
            issues.append(f"Too short: {len(sentences)} sentences (need 6-8)")
        elif len(sentences) > 8:
            issues.append(f"Too long: {len(sentences)} sentences (need 6-8)")

        # "is not" exactly once
        is_not_count = story_text.lower().count("is not")
        if is_not_count == 0:
            issues.append('Missing required "is not" sentence')
        elif is_not_count > 1:
            issues.append(f'"is not" appears {is_not_count} times (must be exactly 1)')

        # No pronouns (word-boundary match to avoid false hits inside "the", "this", etc.)
        import re as _re
        PRONOUN_LIST = ["he", "she", "it", "they", "his", "her", "its", "their", "him", "them"]
        found_pronouns = [p for p in PRONOUN_LIST
                          if _re.search(r'\b' + p + r'\b', story_text.lower())]
        if found_pronouns:
            issues.append(f"Pronouns found: {found_pronouns}")

    # Allowlist check
    words = extract_story_words(path)
    bad = []
    for word, lineno in words:
        if not allowed(word):
            bad.append(f"  line {lineno}: '{word}'")
    if bad:
        issues.append(f"Non-allowlist words ({len(bad)}):")
        issues.extend(bad[:20])  # cap at 20 to keep output readable
        if len(bad) > 20:
            issues.append(f"  ... and {len(bad)-20} more")

    return issues


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        if not os.path.isdir(STORY_DIR):
            print(f"No story directory found: {STORY_DIR}")
            return
        files = sorted(
            os.path.join(STORY_DIR, f)
            for f in os.listdir(STORY_DIR)
            if f.endswith(".md")
        )

    if not files:
        print("No .md files found.")
        return

    total = len(files)
    passed = 0
    failed = 0
    report_lines = []

    for path in files:
        name = os.path.basename(path)
        issues = check_file(path)
        if issues:
            failed += 1
            print(f"FAIL  {name}")
            for iss in issues:
                print(f"      {iss}")
            report_lines.append(f"FAIL {name}")
            report_lines.extend(f"  {i}" for i in issues)
            report_lines.append("")
        else:
            passed += 1
            print(f"PASS  {name}")
            report_lines.append(f"PASS {name}")

    print(f"\n--- {passed}/{total} passed, {failed} failed ---")

    with open(VIOLATIONS_OUT, "w") as f:
        f.write("\n".join(report_lines))
    print(f"Full report written to {VIOLATIONS_OUT}")


if __name__ == "__main__":
    main()
