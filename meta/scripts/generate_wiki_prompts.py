"""
Generate one DeepSeek prompt file per word in tmp/wiki_classification.txt.
Output: tmp/wiki_prompts/<word>.txt (one per word)
"""

import os
import re

REPO = "/home/aomukai/Ninereeds"
CLASSIFICATION = f"{REPO}/tmp/wiki_classification.txt"
OUT_DIR = f"{REPO}/tmp/wiki_prompts"
ALLOWLIST = f"{REPO}/tmp/allowlist_full.txt"

WIKI_OUT_DIR = f"{REPO}/tmp/wiki_output"

os.makedirs(WIKI_OUT_DIR, exist_ok=True)

os.makedirs(OUT_DIR, exist_ok=True)

# Abstract/mass/uncountable nouns — no article
NO_ARTICLE = {
    "acceptance", "accuracy", "addition", "advice", "aid", "air", "algebra",
    "amazement", "attention", "beauty", "boredom", "bravery", "childhood",
    "chance", "code", "conservation", "content", "contrast", "courage",
    "credit", "datum", "death", "debt", "dependence", "determination",
    "development", "difficulty", "domain", "duty", "effort", "electricity",
    "evidence", "exhaustion", "existence", "expansion", "expectation",
    "failure", "focus", "freedom", "frequency", "friendship", "grammar",
    "gratitude", "grief", "growth", "guidance", "hope", "humor",
    "impact", "improvement", "inclusion", "independence", "infinity",
    "information", "inheritance", "inspiration", "intensity", "internet",
    "knowledge", "laughter", "logic", "loneliness", "magic", "maintenance",
    "management", "math", "media", "membership", "motion", "multiplication",
    "music", "mystery", "narrative", "news", "nighttime", "nutrition",
    "opportunity", "participation", "patience", "peace", "permission",
    "plenty", "poetry", "pollution", "population", "pressure", "prevention",
    "pride", "privacy", "probability", "production", "prose", "protection",
    "rotation", "safety", "satisfaction", "scenery", "schoolwork",
    "self-control", "self-knowledge", "similarity", "sportsmanship",
    "storage", "subtraction", "teamwork", "technology", "tension",
    "traffic", "trouble", "trust", "unity", "universe", "validity",
    "vocabulary", "warmth", "well-being", "wildlife",
    "acceptance", "algebra", "analogy", "atom", "beauty", "compromise",
    "courage", "datum", "death", "debt", "demonstrate", "dependence",
    "determination", "development", "dialogue", "dimension", "domain",
    "evidence", "grammar", "independence", "infinity", "logic", "paradox",
    "multiplicity", "prose", "scenery", "similarity", "sportsmanship",
    "subtraction", "multiplication", "addition",
}

# Words that take "an"
AN_WORDS = {
    "adjective", "aim", "analogy", "angle", "ankle", "announcement", "apology",
    "apostrophe", "appearance", "approval", "architect", "area", "article",
    "artist", "assessment", "assignment", "assistance", "assistant",
    "atom", "attempt", "attendance", "attendant", "attention", "auditorium",
    "autumn", "orangutan", "oval", "object", "occasion", "opportunity",
    "opponent", "organization", "origin", "overflow", "omniscient",
    "opal", "outdoor", "umbilical", "unit", "universe", "unknown",
    "utterance", "uncurl", "unbuckle", "unload", "unlock", "untie",
    "insect", "iris", "issue", "item", "ivy", "input", "insight",
    "inspection", "inspiration", "instance", "instruction", "intensity",
    "intent", "interruption", "invitation", "influence", "information",
    "inheritance", "injury", "inverse",
}

# Words that are verbs — question: "what does it mean to X?"
VERB_SET = {
    "arrange", "bite", "bleed", "chew", "connect", "creep", "crouch",
    "demonstrate", "disagree", "disappear", "distribute", "drag",
    "enjoy", "expand", "expect", "introduce", "keep", "lay", "let",
    "loosen", "misunderstand", "nibble", "pee", "pivot", "please",
    "pounce", "poop", "specify", "swipe", "swoop", "thrive",
    "unbuckle", "uncurl", "unload", "unlock", "untie",
}

# Words that are adjectives — question: "what does X mean?"
ADJECTIVE_SET = {
    "accidental", "alive", "allowed", "asleep", "awake", "bored", "bossy",
    "brave", "broken", "complex", "compact", "confused", "daily", "delicious",
    "dense", "dizzy", "excited", "exposed", "friendly", "frustrated",
    "gentle", "glad", "grateful", "hurtful", "jammed", "likely", "lonely",
    "magical", "missed", "narrow", "neat", "omniscient", "outdoor",
    "overwhelmed", "sad", "single", "singular", "specialized", "sorry",
    "steady", "supposed", "unique", "unknown", "verbal", "left", "inverse",
}


def article(word):
    w = word.lower()
    if w in NO_ARTICLE:
        return word
    if w in AN_WORDS or (w[0] in "aeiou" and w not in NO_ARTICLE):
        return f"an {word}"
    return f"a {word}"


def user_question(word):
    w = word.lower()
    if w in VERB_SET:
        return f"what does it mean to {word}?"
    if w in ADJECTIVE_SET:
        return f"what does {word} mean?"
    if w in NO_ARTICLE:
        return f"what is {word}?"
    return f"what is {article(word)}?"


def output_file(safe_name):
    return f"{WIKI_OUT_DIR}/{safe_name}.md"


PROMPT_TEMPLATE = """\
Read {allowlist} — this is the complete list of allowed content words.

Task: write one wiki entry for a child's AI called Ninereeds. Write the finished entry to {outfile}
(This is the only file you should write. Do not write anywhere else.)

REQUIRED FORMAT (copy exactly, including the bracket labels):
[user]{question}
[Ninereeds]<entry here — one paragraph, no line breaks inside>

RULES — follow every one:
1. STRICT ALLOWLIST RULE: Every content word you write must already appear in {allowlist}, or be a standard inflection of a word on that list (walk→walks/walked/walking, slow→slowly, bright→brightly, box→boxes, run→running/ran). If a word you want to use is NOT on the list, stop and pick a simpler synonym that IS on the list. Do not introduce vocabulary that is not already in the file. Function words (the, a, an, is, are, not, to, of, with, in, on, at, by, can, do, does, will, has, have, had, was, were, be, been, and, or, but, so, because, when, that, this, which, who, where, how, what, also, very, more, most, some, many, each, every, all, one, two, three, four, five) are always allowed without checking.
2. The entry is 4 to 6 sentences long. All sentences on one line in the [Ninereeds] paragraph.
3. No pronouns at all. Use nouns instead of he/she/it/they/his/her/its/their.
4. No dialogue. No quotation marks.
5. The final sentence must follow the pattern: "{word} is not [contrasting word or concept]."
   Exactly one "is not" in the entire entry.
6. The entry is factual and concrete. Define what the word means. Give 1-2 examples.
   Do not use fantasy, magic, or fictional framing.
7. Do not use the word "{word}" more than 3 times total.

WORD TO DEFINE: {word}
LEVEL: {level}

Output ONLY the entry block (the [user] line and the [Ninereeds] paragraph).
Do not explain. Do not return a receipt. Do not add headers or extra blank lines.
"""


def parse_classification():
    entries = []
    with open(CLASSIFICATION) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 3:
                print(f"WARNING: bad line: {line!r}")
                continue
            word, level, category = parts
            entries.append((word, level, category))
    return entries


def main():
    entries = parse_classification()
    print(f"Read {len(entries)} entries from classification file.")

    written = 0
    for word, level, category in entries:
        question = user_question(word)
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", word)
        outfile = output_file(safe_name)
        prompt = PROMPT_TEMPLATE.format(
            allowlist=ALLOWLIST,
            outfile=outfile,
            question=question,
            word=word,
            level=level,
        )
        prompt_file = f"{OUT_DIR}/{safe_name}.txt"
        with open(prompt_file, "w") as f:
            f.write(prompt)
        written += 1

    print(f"Wrote {written} prompt files to {OUT_DIR}/")
    print(f"Stories will be written to wiki_1/, wiki_2/, wiki_3/ category files.")


if __name__ == "__main__":
    main()
