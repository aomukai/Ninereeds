"""
Generate one DeepSeek prompt file per tier-1 story, asking for tier-2 expansion.
Reads: tmp/triplet_t1_output/NNN_category_anchor.md (tier-1 story as context)
Reads: tmp/triplet_table.md (anchor + support words)
Output: tmp/triplet_t2_prompts/NNN_anchor.txt
Stories will be written to: tmp/triplet_t2_output/NNN_category_anchor.md
"""

import os
import re

REPO = "/home/aomukai/Ninereeds"
TABLE = f"{REPO}/tmp/triplet_table.md"
T1_DIR = f"{REPO}/tmp/triplet_t1_output"
OUT_DIR = f"{REPO}/tmp/triplet_t2_prompts"
STORY_OUT_DIR = f"{REPO}/tmp/triplet_t2_output"
ALLOWLIST = f"{REPO}/tmp/allowlist_full.txt"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(STORY_OUT_DIR, exist_ok=True)

# Approved character names — confirmed on allowlist
CHARACTERS = [
    "cody", "ella", "emma", "jack", "lily", "luke",
    "max", "noah", "nora", "owen", "sophie", "toby", "will",
]

def pick_character(num):
    return CHARACTERS[(num - 1) % len(CHARACTERS)]


PROMPT_TEMPLATE = """\
Read {allowlist} — this is the complete list of allowed content words for this story.

Task: write one tier-2 story for a child's AI called Ninereeds. Write the finished story to {outfile}

TIER-1 STORY (the simpler version you are expanding):
---
{t1_story}
---

REQUIRED FORMAT (copy exactly, including the bracket labels):
[user]tell me a story about {prompt_line}.
[Ninereeds]<story here>

RULES — follow every one:
1. The story is 10 to 14 sentences long.
2. Both support words must appear naturally: {sup1} and {sup2}.
3. Introduce one named character: {character} (capitalize the name).
4. Include exactly 1 or 2 dialogue exchanges — a character speaks one or two lines using quotation marks.
5. Pronouns are allowed (he, she, it, they, his, her, its, their, him, them).
6. Every content word in the story must be on the allowlist or a natural inflection of an allowed word.
   Allowed inflections: walk→walks/walked/walking; slow→slowly; bright→brightly.
   Function words (the, a, and, is, not, to, in, of, that, etc.) are always allowed.
7. The scene is concrete and realistic. No fantasy, no magic.
8. Build on the same scenario as the tier-1 story above, but add the character, expand the events, and include dialogue.

ANCHOR WORD: {anchor}
SUPPORT WORD 1: {sup1}
SUPPORT WORD 2: {sup2}
CHARACTER NAME: {character}

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


def prompt_article(anchor):
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
        "paradox", "dimension", "contrast", "development",
    }
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
    a = anchor.lower()
    if a in NO_ARTICLE:
        return anchor
    if a in AN_WORDS or (a[0] in "aeiou" and a not in NO_ARTICLE):
        return f"an {anchor}"
    return f"a {anchor}"


def load_t1_story(num, category, anchor):
    path = os.path.join(T1_DIR, f"{num:03d}_{category}_{anchor}.md")
    if not os.path.exists(path):
        return None, path
    with open(path) as f:
        return f.read().strip(), path


def main():
    rows = parse_table()
    print(f"Parsed {len(rows)} rows from triplet table.")
    missing_t1 = []

    for row in rows:
        num = row["num"]
        anchor = row["anchor"]
        category = row["category"]

        t1_story, t1_path = load_t1_story(num, category, anchor)
        if t1_story is None:
            missing_t1.append(t1_path)
            continue

        character = pick_character(num)
        outfile = f"{STORY_OUT_DIR}/{num:03d}_{category}_{anchor}.md"

        prompt = PROMPT_TEMPLATE.format(
            allowlist=ALLOWLIST,
            outfile=outfile,
            prompt_line=prompt_article(anchor),
            anchor=anchor,
            sup1=row["sup1"],
            sup2=row["sup2"],
            hint=row["hint"],
            character=character,
            t1_story=t1_story,
        )

        prompt_file = f"{OUT_DIR}/{num:03d}_{anchor}.txt"
        with open(prompt_file, "w") as f:
            f.write(prompt)

    written = len(rows) - len(missing_t1)
    print(f"Wrote {written} prompt files to {OUT_DIR}/")
    print(f"Stories will be written to {STORY_OUT_DIR}/")
    if missing_t1:
        print(f"WARNING: {len(missing_t1)} tier-1 files not found:")
        for p in missing_t1:
            print(f"  {p}")


if __name__ == "__main__":
    main()
