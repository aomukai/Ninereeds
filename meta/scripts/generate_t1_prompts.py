"""
Generate one DeepSeek prompt file per row of tmp/triplet_table.md.
Output: tmp/triplet_t1_prompts/NNN_anchor.txt (one per story)
"""

import os
import re

REPO = "/home/aomukai/Ninereeds"
TABLE = f"{REPO}/tmp/triplet_table.md"
OUT_DIR = f"{REPO}/tmp/triplet_t1_prompts"
STORY_OUT_DIR = f"{REPO}/tmp/triplet_t1_output"
ALLOWLIST = f"{REPO}/tmp/allowlist_full.txt"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(STORY_OUT_DIR, exist_ok=True)

# Words that take no article (abstract, uncountable, mass nouns, adjectives-as-concepts)
NO_ARTICLE = {
    "acceptance", "accuracy", "adulthood", "advice", "aid", "air", "algebra",
    "amazement", "autumn", "beauty", "boredom", "bravery", "braveness",
    "brave", "calm", "cargo", "chance", "chatter", "childhood", "choice",
    "cleanup", "code", "conservation", "content", "contrast",
    "courage", "creation", "credit", "daily", "death", "debt", "development",
    "difficulty", "determination", "disappear", "disorder",
    "domain", "dough", "duty", "effort", "electricity", "equipment",
    "escalation", "evidence", "exclusion", "exhaustion", "existence",
    "expansion", "expectation", "failure", "fiber", "focus", "format",
    "freedom", "frequency", "friendship", "grammar", "gradation", "gratitude",
    "grief", "growth", "guidance", "hope", "hue", "humor", "impact",
    "improvement", "inclusion", "independence", "infinity", "information",
    "inheritance", "inspiration", "intensity", "internet", "knowledge",
    "laughter", "location", "loneliness", "magic", "maintenance",
    "management", "math", "media", "membership", "motion", "multiplication",
    "music", "mystery", "narrative", "news", "nighttime", "nutrition",
    "opportunity", "origin", "participation", "patience", "peace",
    "permission", "plenty", "poetry", "pollution", "population",
    "pressure", "prevention", "pride", "privacy", "probability",
    "production", "prose", "protection", "prose", "rotation",
    "safety", "satisfaction", "scenery", "schoolwork", "self-control",
    "self-knowledge", "similarity", "sportsmanship", "storage", "subtraction",
    "suffix", "teamwork", "technology", "tension", "traffic", "trouble",
    "trust", "unity", "universe", "validity", "vocabulary", "warmth",
    "well-being", "wildlife",
    # abstract/process anchors from our table
    "paradox", "dimension", "contrast", "development",
}

# Words that take "an" (start with vowel sound)
AN_WORDS = {
    "algorithm", "alphabet", "angle", "ankle", "announcement", "apostrophe",
    "apology", "appearance", "approval", "architect", "area", "article",
    "artist", "assessment", "assignment", "assistance", "assistant",
    "atom", "attempt", "attendance", "attendant", "attention", "attribute",
    "audience", "auditorium", "autumn", "ecologist", "ecosystem",
    "edition", "effort", "election", "electron", "element",
    "emergency", "enemy", "entry", "environment",
    "image", "improvement", "improbability", "implication",
    "inclusion", "independence", "infinity", "influence", "ingredient",
    "inheritance", "injury", "input", "insight", "inspection", "inspiration",
    "instance", "instruction", "intensity", "intent", "interruption",
    "invitation", "iris", "issue", "item", "ivy",
    "object", "occasion", "opportunity", "opponent", "organization", "origin",
    "oval", "overflow", "ecosystem", "ecologist",
    "umbrella", "unit", "universe", "unknown",
    "utterance",
}

def prompt_article(anchor):
    a = anchor.lower()
    if a in NO_ARTICLE:
        return anchor
    if a in AN_WORDS or (a[0] in "aeiou" and a not in NO_ARTICLE):
        return f"an {anchor}"
    return f"a {anchor}"


PROMPT_TEMPLATE = """\
Read {allowlist} — this is the complete list of allowed words for this story.

Task: write one story for a child's AI called Ninereeds. Write the finished story to {outfile}

REQUIRED FORMAT (copy exactly, including the bracket labels):
[user]tell me a story about {prompt_line}.
[Ninereeds]<story here>

RULES — follow every one:
1. The story is 6 to 8 sentences long.
2. Both of these words must appear naturally in the story: {sup1} and {sup2}.
3. Exactly one sentence in the story uses the phrase "is not".
4. No pronouns at all. Use nouns instead of he/she/it/they/his/her/its/their/him/her.
5. No dialogue. No quotation marks.
6. Every word in the story must be on the allowlist or a natural inflection of an allowed word.
   Allowed inflections: walk→walks/walked/walking; slow→slowly; bright→brightly.
   Not allowed: words that have no base form on the allowlist.
7. The scene is concrete and realistic. No fantasy, no magic.

ANCHOR WORD: {anchor}
SUPPORT WORD 1: {sup1}
SUPPORT WORD 2: {sup2}
SCENARIO HINT: {hint}

Output ONLY the story block (the [user] line and the [Ninereeds] paragraph).
Do not explain. Do not return a receipt. Do not add headers.
"""


def parse_table():
    rows = []
    current_cat = None
    with open(TABLE) as f:
        for line in f:
            if line.startswith("## "):
                current_cat = line.strip().lstrip("# ").split(" (")[0].strip()
            if line.startswith("| ") and not line.startswith("| #") and not line.startswith("|---"):
                cols = [c.strip() for c in line.split("|")[1:-1]]
                if len(cols) >= 5 and cols[0].isdigit():
                    rows.append({
                        "num": int(cols[0]),
                        "category": current_cat,
                        "anchor": cols[1],
                        "sup1": cols[2],
                        "sup2": cols[3],
                        "hint": cols[4],
                    })
    return rows


def make_prompt(row):
    anchor = row["anchor"]
    outfile = f"{STORY_OUT_DIR}/{row['num']:03d}_{row['category']}_{anchor}.md"
    return PROMPT_TEMPLATE.format(
        allowlist=ALLOWLIST,
        outfile=outfile,
        prompt_line=prompt_article(anchor),
        anchor=anchor,
        sup1=row["sup1"],
        sup2=row["sup2"],
        hint=row["hint"],
    ), outfile


def main():
    rows = parse_table()
    print(f"Parsed {len(rows)} rows from triplet table.")
    for row in rows:
        prompt, outfile = make_prompt(row)
        prompt_file = f"{OUT_DIR}/{row['num']:03d}_{row['anchor']}.txt"
        with open(prompt_file, "w") as f:
            f.write(prompt)
    print(f"Wrote {len(rows)} prompt files to {OUT_DIR}/")
    print(f"Stories will be written to {STORY_OUT_DIR}/")


if __name__ == "__main__":
    main()
