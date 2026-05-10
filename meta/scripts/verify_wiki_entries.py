"""
Verify wiki entries in tmp/wiki_output/*.md against the allowlist.
Rules: [user]/[Ninereeds] format, 4-6 sentences, no pronouns, one "is not", allowlist compliance.
Writes summary to tmp/wiki_violations.txt
"""

import os
import re
import sys

REPO = "/home/aomukai/Ninereeds"
ALLOWLIST_PATH = f"{REPO}/tmp/allowlist_full.txt"
WIKI_OUT_DIR = f"{REPO}/tmp/wiki_output"
VIOLATIONS_OUT = f"{REPO}/tmp/wiki_violations.txt"

with open(ALLOWLIST_PATH) as f:
    ALLOWLIST = set(w.strip().lower() for w in f if w.strip())

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
    "first", "second", "third", "fourth", "fifth", "sixth", "seventh",
    "eighth", "ninth", "tenth", "finally", "next", "last",
    "ever", "never", "though", "yet", "once", "twice",
    "am", "is", "are", "was", "were", "be", "been", "being",
    "ful", "less", "do", "does", "did", "have", "has", "had",
    "can", "could", "will", "would", "should", "may", "might", "must",
    "shall", "need", "dare", "used",
    "about", "above", "after", "as", "at", "by", "for", "from",
    "in", "into", "of", "off", "on", "onto", "out", "over",
    "per", "than", "the", "to", "up", "with",
    "a", "an",
    # Note: no pronouns — wiki entries must not use them
}

STRIP_SUFFIXES = [
    "iest", "ier", "ness", "ment", "tion", "sion",
    "ling", "ting", "ning", "ying", "ing", "ied", "est",
    "er", "ly", "ed", "es", "s", "en",
]

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
    "knelt": "kneel", "crept": "creep", "drank": "drink", "spat": "spit",
    "bit": "bite", "bound": "bind", "bent": "bend", "bled": "bleed",
    "blew": "blow", "bred": "breed", "clung": "cling",
    "dealt": "deal", "dreamt": "dream", "felt": "feel", "fled": "flee",
    "flung": "fling", "forgave": "forgive",
    "ground": "grind", "lent": "lend", "leapt": "leap", "learnt": "learn",
    "shook": "shake", "shone": "shine", "shrank": "shrink",
    "slung": "sling", "snuck": "sneak", "spun": "spin",
    "stung": "sting", "strode": "stride", "strung": "string",
    "struck": "strike", "swore": "swear", "wept": "weep",
    "wound": "wind", "wrung": "wring",
}

PRONOUN_WORDS = {
    "i", "me", "my", "myself", "we", "us", "our", "ours", "ourselves",
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "it", "its", "itself",
    "they", "them", "their", "theirs", "themselves",
    "you", "your", "yours", "yourself", "yourselves",
}


def allowed(word):
    w = word.lower().strip(".,!?;:\"'()-—")
    if not w or w.isdigit():
        return True
    if w in FUNCTION_WORDS:
        return True
    if w.endswith("'s"):
        w = w[:-2]
    elif w.endswith("s'"):
        w = w[:-1]
    if not w:
        return True
    if w in ALLOWLIST:
        return True
    for sfx in STRIP_SUFFIXES:
        if w.endswith(sfx) and len(w) - len(sfx) >= 2:
            base = w[: -len(sfx)]
            if base in ALLOWLIST:
                return True
            if base + "e" in ALLOWLIST:
                return True
            if len(base) >= 2 and base[-1] == base[-2]:
                if base[:-1] in ALLOWLIST:
                    return True
            if sfx == "ing" and w.endswith("ying"):
                if w[:-4] + "y" in ALLOWLIST:
                    return True
    if w.endswith("ied") and w[:-3] + "y" in ALLOWLIST:
        return True
    if w.endswith("ies") and w[:-3] + "y" in ALLOWLIST:
        return True
    if w in IRREGULAR and IRREGULAR[w] in ALLOWLIST:
        return True
    return False


def extract_entry_words(path):
    words = []
    in_entry = False
    with open(path) as f:
        for lineno, line in enumerate(f, 1):
            stripped = line.strip()
            if stripped.startswith("[Ninereeds]"):
                in_entry = True
                text = stripped[len("[Ninereeds]"):]
            elif stripped.startswith("[user]"):
                in_entry = False
                continue
            elif in_entry:
                text = stripped
            else:
                continue
            for tok in re.split(r"[\s\-]+", text):
                clean = tok.lower().strip(".,!?;:\"'()—")
                if clean:
                    words.append((clean, lineno))
    return words


def check_file(path):
    issues = []
    if not os.path.exists(path):
        return [f"FILE MISSING: {path}"]

    with open(path) as f:
        content = f.read()

    if "[user]" not in content:
        issues.append("Missing [user] line")
        return issues
    if "[Ninereeds]" not in content:
        issues.append("Missing [Ninereeds] block")
        return issues

    ninereeds_block = re.search(r"\[Ninereeds\](.*)", content, re.DOTALL)
    if ninereeds_block:
        story_text = ninereeds_block.group(1).strip()
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", story_text) if s.strip()]
        if len(sentences) < 4:
            issues.append(f"Too short: {len(sentences)} sentences (need 4-6)")
        elif len(sentences) > 6:
            issues.append(f"Too long: {len(sentences)} sentences (need 4-6)")

        is_not_count = len(re.findall(r'\bis not\b', story_text))
        if is_not_count == 0:
            issues.append('Missing "is not" contrast sentence')
        elif is_not_count > 1:
            issues.append(f'Too many "is not" ({is_not_count}, need exactly 1)')

        # Check for pronouns (not allowed in wiki entries)
        text_lower = story_text.lower()
        for pronoun in PRONOUN_WORDS:
            if re.search(r'\b' + pronoun + r'\b', text_lower):
                issues.append(f'Pronoun found: "{pronoun}" (not allowed in wiki entries)')

        # "is not" should be in the last sentence
        if sentences and "is not" not in sentences[-1].lower():
            issues.append('"is not" not in final sentence')

    words = extract_entry_words(path)
    bad = []
    for word, lineno in words:
        if not allowed(word):
            bad.append(f"  line {lineno}: '{word}'")
    if bad:
        issues.append(f"Non-allowlist words ({len(bad)}):")
        issues.extend(bad[:20])
        if len(bad) > 20:
            issues.append(f"  ... and {len(bad)-20} more")

    return issues


def main():
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        if not os.path.isdir(WIKI_OUT_DIR):
            print(f"No output directory found: {WIKI_OUT_DIR}")
            return
        files = sorted(
            os.path.join(WIKI_OUT_DIR, f)
            for f in os.listdir(WIKI_OUT_DIR)
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
