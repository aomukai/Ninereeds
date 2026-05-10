"""
Generate one DeepSeek prompt file per tier-2 story, asking for tier-3 expansion.
Tier 3 adds causal reasoning: "because", "so", cause-effect chains, 3-paragraph structure.
Reads: tmp/triplet_t2_output/NNN_category_anchor.md (tier-2 story as context)
Reads: tmp/triplet_table.md (anchor + support words)
Output: tmp/triplet_t3_prompts/NNN_anchor.txt
Stories will be written to: tmp/triplet_t3_output/NNN_category_anchor.md
"""

import os
import re

REPO = "/home/aomukai/Ninereeds"
TABLE = f"{REPO}/tmp/triplet_table.md"
T2_DIR = f"{REPO}/tmp/triplet_t2_output"
OUT_DIR = f"{REPO}/tmp/triplet_t3_prompts"
STORY_OUT_DIR = f"{REPO}/tmp/triplet_t3_output"
ALLOWLIST = f"{REPO}/tmp/allowlist_full.txt"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(STORY_OUT_DIR, exist_ok=True)

CHARACTERS = [
    "cody", "ella", "emma", "jack", "lily", "luke",
    "max", "noah", "nora", "owen", "sophie", "toby", "will",
]

def pick_character(num):
    return CHARACTERS[(num - 1) % len(CHARACTERS)]


PROMPT_TEMPLATE = """\
Read {allowlist} — this is the complete list of allowed content words for this story.

Task: write one tier-3 story for a child's AI called Ninereeds. Write the finished story to {outfile}

TIER-2 STORY (the version you are expanding):
---
{t2_story}
---

REQUIRED FORMAT (copy exactly, including the bracket labels):
[user]tell me a story about {prompt_line}.
[Ninereeds]<paragraph 1>

<paragraph 2>

<paragraph 3>

RULES — follow every one:
1. The story has exactly 3 paragraphs, each 3-5 sentences long (total 9-14 sentences).
2. Both support words must appear naturally: {sup1} and {sup2}.
3. Use the same character as tier-2: {character} (capitalize the name).
4. Use "because" at least twice and "so" at least once to show cause and effect.
5. Include 1-2 dialogue lines using quotation marks (place the dialogue in paragraph 2).
6. Pronouns are allowed (he, she, it, they, his, her, its, their, him, them).
7. Every content word must be on the allowlist or a natural inflection of an allowed word.
   Function words (the, a, and, is, not, to, in, of, that, etc.) are always allowed.
8. The scene is concrete and realistic. No fantasy, no magic.
9. Build on the same scenario as the tier-2 story above. Deepen the causal connections.

ANCHOR WORD: {anchor}
SUPPORT WORD 1: {sup1}
SUPPORT WORD 2: {sup2}
CHARACTER NAME: {character}

Output ONLY the story block (the [user] line and the [Ninereeds] paragraphs, with blank lines between paragraphs).
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
        "amazement", "autumn", "beauty", "boredom", "bravery", "calm", "cargo",
        "chance", "chatter", "childhood", "choice", "cleanup", "code",
        "conservation", "content", "contrast", "courage", "creation", "credit",
        "daily", "death", "debt", "development", "difficulty", "determination",
        "disappear", "disorder", "domain", "dough", "duty", "effort",
        "electricity", "equipment", "escalation", "evidence", "exclusion",
        "exhaustion", "existence", "expansion", "expectation", "failure",
        "fiber", "focus", "format", "freedom", "frequency", "friendship",
        "grammar", "gradation", "gratitude", "grief", "growth", "guidance",
        "hope", "hue", "humor", "impact", "improvement", "inclusion",
        "independence", "infinity", "information", "inheritance", "inspiration",
        "intensity", "internet", "knowledge", "laughter", "location",
        "loneliness", "magic", "maintenance", "management", "math", "media",
        "membership", "motion", "multiplication", "music", "mystery",
        "narrative", "news", "nighttime", "nutrition", "opportunity", "origin",
        "participation", "patience", "peace", "permission", "plenty", "poetry",
        "pollution", "population", "pressure", "prevention", "pride", "privacy",
        "probability", "production", "prose", "protection", "rotation",
        "safety", "satisfaction", "scenery", "schoolwork", "self-control",
        "self-knowledge", "similarity", "sportsmanship", "storage", "subtraction",
        "suffix", "teamwork", "technology", "tension", "traffic", "trouble",
        "trust", "unity", "universe", "validity", "vocabulary", "warmth",
        "well-being", "wildlife", "paradox", "dimension", "contrast", "development",
    }
    AN_WORDS = {
        "algorithm", "alphabet", "angle", "ankle", "announcement", "apostrophe",
        "apology", "appearance", "approval", "architect", "area", "article",
        "artist", "assessment", "assignment", "assistance", "assistant",
        "atom", "attempt", "attendance", "attention", "attribute", "audience",
        "auditorium", "ecologist", "ecosystem", "edition", "effort", "election",
        "electron", "element", "emergency", "enemy", "entry", "environment",
        "image", "improvement", "inclusion", "independence", "infinity",
        "influence", "ingredient", "inheritance", "injury", "input", "insight",
        "inspiration", "instance", "instruction", "intensity", "intent",
        "interruption", "invitation", "iris", "issue", "item", "object",
        "occasion", "opportunity", "opponent", "organization", "origin",
        "umbrella", "unit", "universe", "unknown", "utterance",
    }
    a = anchor.lower()
    if a in NO_ARTICLE:
        return anchor
    if a in AN_WORDS or (a[0] in "aeiou" and a not in NO_ARTICLE):
        return f"an {anchor}"
    return f"a {anchor}"


CHARACTER_SET = set(CHARACTERS)

def load_story(directory, num, category, anchor):
    path = os.path.join(directory, f"{num:03d}_{category}_{anchor}.md")
    if not os.path.exists(path):
        return None, path
    with open(path) as f:
        return f.read().strip(), path


def extract_character(story_text, fallback_num):
    """Find the character name actually used in a story, fall back to deterministic assignment."""
    for name in CHARACTER_SET:
        if re.search(r'\b' + name + r'\b', story_text.lower()):
            return name
    return pick_character(fallback_num)


def main():
    rows = parse_table()
    print(f"Parsed {len(rows)} rows from triplet table.")
    missing_t2 = []

    for row in rows:
        num = row["num"]
        anchor = row["anchor"]
        category = row["category"]

        t2_story, t2_path = load_story(T2_DIR, num, category, anchor)
        if t2_story is None:
            missing_t2.append(t2_path)
            continue

        character = extract_character(t2_story, num)
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
            t2_story=t2_story,
        )

        prompt_file = f"{OUT_DIR}/{num:03d}_{anchor}.txt"
        with open(prompt_file, "w") as f:
            f.write(prompt)

    written = len(rows) - len(missing_t2)
    print(f"Wrote {written} prompt files to {OUT_DIR}/")
    print(f"Stories will be written to {STORY_OUT_DIR}/")
    if missing_t2:
        print(f"WARNING: {len(missing_t2)} tier-2 files not found (will be skipped):")
        for p in missing_t2:
            print(f"  {p}")


if __name__ == "__main__":
    main()
