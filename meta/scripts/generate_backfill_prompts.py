#!/usr/bin/env python3
"""
Generate lean prompt files for the backfill run.

Usage:
    python3 generate_backfill_prompts.py --phase 1 --pos nouns [--batch-size 8]

Outputs prompt files to tmp/backfill_prompts/phase_N_pos_NNNN.txt
Each prompt covers one batch (default 8 words).
Skips words already in the progress ledger.

Progress ledger: training_data/phases/backfill_progress.txt
  Format: DONE phase_N/phase_N_NNNN.md  [word]

Output format DeepSeek is asked to use:
  %%% FILE: phase_N/phase_N_NNNN.md WORD: the_word %%%
  [file content]
  %%% END FILE %%%
"""

import argparse
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VOCAB = REPO / "vocab"
PHASES_DIR = REPO / "training_data" / "phases"
PROMPTS_DIR = REPO / "tmp" / "backfill_prompts"
PROGRESS_FILE = PHASES_DIR / "backfill_progress.txt"

# ── File number format per phase ──────────────────────────────────────
# Determined by examining existing files
FILE_NUM_FORMAT = {
    1: "04d",   # phase_1_1250.md
    2: "03d",   # phase_2_355.md
    3: "03d",   # phase_3_601.md
    4: "03d",   # phase_4_096.md
    5: "04d",   # phase_5_2002.md
    6: "04d",   # phase_6_1169.md
}

NEXT_FILE_NUM = {
    1: 1250,
    2: 355,
    3: 601,
    4: 96,
    5: 2002,
    6: 1169,
}

LINES_PER_FILE = {
    "nouns_1": 31, "nouns_2": 31, "nouns_3": 31, "nouns_6": 31,
    "nouns_4": 6,  "nouns_5": 6,
    "verbs_1": 31, "verbs_2": 31, "verbs_3": 31, "verbs_4": 31,
    "verbs_5": 31, "verbs_6": 31,
    "adjectives_1": 4, "adjectives_2": 4, "adjectives_3": 4, "adjectives_4": 4,
    "adjectives_5": 4, "adjectives_6": 4,
}

# ── Templates (embedded, keyed by phase×pos) ─────────────────────────

NOUN_TEMPLATES = {
    1: """\
[user]What does [the/a] [word] look like?
[Ninereeds][The/A] [word] is [physical property].
[The/A] [word] is [physical property].
[The/A] [word] is [physical property].
[The/A] [word] [verb — size/colour/texture/shape].
[The/A] [word] [verb — appearance detail].
[The/A] [word] is [property A] and [property B].

[user]Where can you find [the/a] [word]?
[Ninereeds][The/A] [word] is [location].
[The/A] [word] is [location].
[The/A] [word] is [location].
[The/A] [word] [verb] [location].
[The/A] [word] [verb] [location].
[The/A] [word] is [location A] and [location B].

[user]What does [the/a] [word] do?
[Ninereeds][The/A] [word] [action].
[The/A] [word] [action].
[The/A] [word] [action].
[The/A] [word] [action].
[The/A] [word] [action].
[The/A] [word] is [verb-A] and [verb-B].

[user]What does [the/a] [word] give?
[Ninereeds][The/A] [word] gives [output].
[The/A] [word] [effect on world].
[The/A] [word] [effect on world].
[The/A] [word] [effect on world].
[The/A] [word] [effect on world].
[The/A] [word] is [A] and [B].

Rules:
- Q1: physical properties (shape, colour, size, texture, temperature)
- Q2: real locations the word is found in or near
- Q3: what it naturally does (process, behaviour, change)
- Q4: what it produces or provides
- "the" for uncountable/unique (wind, rain, fire, sky); "a" for countable (apple, stone, dog)
- Summary line (line 7 of each block): two distinct properties from that block, joined with "and"
- No pronouns (it, its, they). No negation. Capital first letter, period at end. 31 lines, no trailing blank.""",

    2: """\
[user]What does a [word] look like?
[Ninereeds]A [word] is [description].
A [word] is [description].
A [word] is [description].
A [word] is [description].
A [word] is [description].
A [word] is [property A] and [property B].

[user]Where can you find a [word]?
[Ninereeds]A [word] is [location].
A [word] is [location].
A [word] is [location].
A [word] is [location].
A [word] is [location].
A [word] is [location A] and [location B].

[user]How does a [word] behave?
[Ninereeds]A [word] [behaviour].
A [word] [behaviour].
A [word] [behaviour].
A [word] [behaviour].
A [word] [behaviour].
A [word] [behaviour A] and [behaviour B].

[user]What does a [word] do?
[Ninereeds]A [word] [function].
A [word] [function].
A [word] [function].
A [word] [function].
A [word] [function].
A [word] [function A] and [function B].

Rules:
- Use "a" (or "an" if word starts with vowel sound) throughout
- Q3: how the thing acts, responds, or operates when used
- Q4: its purpose and role
- Summary line: combine two distinct ideas from that block with "and"
- No pronouns. No negation. 31 lines, no trailing blank.""",

    3: """\
[user]What is [a/an/bare] [word]?
[Ninereeds][Word] is [definition].
[Word] is [definition or characteristic].
[Word] is [characteristic].
[Word] is [characteristic].
[Word] is [characteristic].
[Word] is [property A] and [property B].

[user]Where does [word] occur?
[Ninereeds][Word] occurs [context/location].
[Word] occurs [context].
[Word] occurs [context].
[Word] occurs [context].
[Word] occurs [context].
[Word] occurs [context A] and [context B].

[user]What does [word] do?
[Ninereeds][Word] [action/effect].
[Word] [action/effect].
[Word] [action/effect].
[Word] [action/effect].
[Word] [action/effect].
[Word] [action A] and [action B].

[user]What does [word] give?
[Ninereeds][Word] is for [purpose].
[Word] is for [purpose].
[Word] is for [purpose].
[Word] is for [purpose].
[Word] is for [purpose].
[Word] is for [purpose A] and [purpose B].

Rules:
- Q1: "What is a/an X?" for countable abstracts; "What is X?" for mass abstracts
- Q4: "X is for [purpose]." pattern
- No article on noun in Q3/Q4 questions for mass abstracts
- No pronouns. No negation. 31 lines, no trailing blank.""",

    4: """\
[user]What happens to [a/the/bare] [word]?
[Ninereeds][Setup — initial state].
[Action — first change].
[Action — second change].
[Result — completion].
[Summary — what the word is, defined by the process].

Rules:
- 6 lines total. No blank lines. No trailing blank.
- Lines tell a mini-story: state → change → change → result → definition
- Last line: "[Word] is [what it is in one clause]."
- Question variants: "What happens in a X?" / "How does X form?" / "Where does X go?"
- No pronouns. No negation.""",

    5: """\
[user]What does a [word] do?
[Ninereeds]The [word] [initial action].
The [word] [movement toward goal].
The [word] [reaches/arrives at goal].
The [word] [completes the action].
The [word] [combines key actions in one clause].

Rules:
- 6 lines total. No blank lines. No trailing blank.
- Lines form a purposeful sequence: start → move → arrive → act → summary
- Last line: "The [word] [verb 1] to [verb 2]."
- Subject is always "The [word]" — no pronouns. No negation.""",

    6: """\
[user]What does [word] look like?
[Ninereeds][Word] is [concrete manifestation].
[Word] is [concrete manifestation].
[Word] is [concrete manifestation].
[Word] is [concrete manifestation].
[Word] is [concrete manifestation].
[Word] is [A] and [B].

[user]Where does [word] appear?
[Ninereeds][Word] is [source/context].
[Word] is [source/context].
[Word] is [source/context].
[Word] is [location/context].
[Word] is [location/context].
[Word] is [context A] and [context B].

[user]What does [word] do?
[Ninereeds][Word] is [function as gerund/noun phrase].
[Word] is [function].
[Word] is [function].
[Word] is [function].
[Word] is [function].
[Word] is [function A] and [function B].

[user]What does [word] give?
[Ninereeds][Word] is for [purpose].
[Word] is for [purpose].
[Word] is for [purpose].
[Word] is for [purpose].
[Word] is for [purpose].
[Word] is for [purpose A] and [purpose B].

Rules:
- No article on the noun in questions or body lines
- Q1: concrete examples of what the abstract concept looks like in practice
- Q3: gerund phrases ("Output is showing information.")
- Q4: "X is for Y." pattern
- No pronouns. No negation. 31 lines, no trailing blank.""",
}

VERB_TEMPLATE = """\
[user]what is [xing]?
[Ninereeds][Xing] is [definition sentence].
[Xing] is [description 2].
[Xing] is [description 3].
[Xing] is [description 4].
[Xing] is [description 5].
[Xing] is [property A] and [property B].

[user]when does [xing] happen?
[Ninereeds][Xing] happens when [condition 1].
[Xing] happens when [condition 2].
[Xing] happens [context 3].
[Xing] happens [context 4].
[Xing] happens [context 5].
[Xing] happens [condition A] and [condition B].

[user]what does [xing] bring?
[Ninereeds][Xing] brings [outcome 1].
[Xing] brings [outcome 2].
[Xing] brings [outcome 3].
[Xing] brings [outcome 4].
[Xing] brings [outcome 5].
[Xing] brings [outcome A] and [outcome B].

[user]what is [xing] for?
[Ninereeds][Xing] is for [purpose 1].
[Xing] is for [purpose 2].
[Xing] is for [purpose 3].
[Xing] is for [purpose 4].
[Xing] is for [purpose 5].
[Xing] is for [purpose A] and [purpose B].

Rules (ALL PHASES):
- [user] tag lowercase. [Ninereeds] tag + body on same line, no space.
- Gerund [xing] is LOWERCASE in both question and body.
- Summary line: "[Xing] is [A] and [B]." (Q1/Q3/Q4) or "[Xing] happens [A] and [B]." (Q2)
- One blank line between block pairs. NO trailing blank after block 4.
- No negation ("not", "no", "never", "cannot"). No pronouns ("it", "they", "he", "she").
- All body lines: capital first letter, end with period.
- 31 lines total."""

ADJ_TEMPLATE = """\
[user]What does [x] mean?
[Ninereeds][X] describes something.
[Positive example 1]. [Positive example 2]. [Positive example 3].
[Negative example 1]. [Negative example 2]. [Negative example 3].

Rules:
- Exactly 4 lines. No blank lines anywhere.
- Line 1: [user]What does [x] mean? — word is LOWERCASE in question
- Line 2: [Ninereeds][X] describes something. — word is CAPITALISED
- Line 3: exactly 3 POSITIVE examples. Pattern: "[Subject] is [adjective]." — 3 sentences.
- Line 4: exactly 3 NEGATIVE examples. Pattern: "[Subject] is not [adjective]." — 3 sentences.
- Short familiar nouns or gerunds as subjects. No repeated subjects across lines 3 and 4."""


def load_progress():
    """Return set of (filename) already done."""
    if not PROGRESS_FILE.exists():
        return set()
    done = set()
    for line in PROGRESS_FILE.read_text().splitlines():
        m = re.match(r'^DONE\s+(\S+)', line)
        if m:
            done.add(m.group(1))
    return done


def get_next_file_num(phase):
    """Read the phases directory and return the highest existing number + 1."""
    phase_dir = PHASES_DIR / f"phase_{phase}"
    if not phase_dir.exists():
        return NEXT_FILE_NUM[phase]
    fmt = FILE_NUM_FORMAT[phase]
    pat = re.compile(rf"phase_{phase}_(\d+)\.md$")
    nums = [int(m.group(1)) for f in phase_dir.iterdir()
            if (m := pat.match(f.name))]
    return max(nums, default=NEXT_FILE_NUM[phase] - 1) + 1


def build_prompt(phase, pos, word_list, file_map):
    """Build a prompt that tells DeepSeek to write files at exact paths."""
    if pos == "nouns":
        template = NOUN_TEMPLATES[phase]
    elif pos == "verbs":
        template = VERB_TEMPLATE
    else:
        template = ADJ_TEMPLATE

    expected_lines = {
        ("nouns", 1): 31, ("nouns", 2): 31, ("nouns", 3): 31, ("nouns", 6): 31,
        ("nouns", 4): 6,  ("nouns", 5): 6,
        ("verbs", 1): 31, ("verbs", 2): 31, ("verbs", 3): 31, ("verbs", 4): 31,
        ("verbs", 5): 31, ("verbs", 6): 31,
        ("adjectives", 1): 4, ("adjectives", 2): 4, ("adjectives", 3): 4,
        ("adjectives", 4): 4, ("adjectives", 5): 4, ("adjectives", 6): 4,
    }.get((pos, phase), 31)

    lines = []
    lines.append("Write these Ninereeds training files using the write tool. Write each file immediately.")
    lines.append("")
    lines.append("FORMAT:")
    lines.append(template)
    lines.append("")
    if pos == "nouns" and phase in (1, 2, 3, 6):
        lines.append(f"Each file: exactly {expected_lines} lines. No pronouns (it/its/they). No negation.")
        lines.append("Summary line (line 7 of each block): use 'and', not 'or'.")
    elif pos == "nouns" and phase in (4, 5):
        lines.append(f"Each file: exactly {expected_lines} lines. No pronouns. No negation.")
    elif pos == "verbs":
        lines.append(f"Each file: exactly {expected_lines} lines. Gerund lowercase throughout. No pronouns. No negation.")
    else:
        lines.append("Each file: exactly 4 lines, no blank lines.")
    lines.append("")
    lines.append("FILES:")
    for word in word_list:
        fname = file_map[word]
        full_path = f"training_data/phases/{fname}"
        lines.append(f"  '{word}' → {full_path}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", type=int, required=True, choices=range(1, 7))
    parser.add_argument("--pos", required=True, choices=["nouns", "verbs", "adjectives"])
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    phase, pos = args.phase, args.pos
    queue_file = VOCAB / f"phase_{phase}_{pos}_new.txt"
    if not queue_file.exists():
        print(f"Queue file not found: {queue_file}")
        return

    words = [l.strip().lower() for l in queue_file.read_text().splitlines() if l.strip()]
    if not words:
        print("Queue is empty.")
        return

    done = load_progress()
    # Build done set by word (extract word from progress entries)
    done_words = set()
    if PROGRESS_FILE.exists():
        for line in PROGRESS_FILE.read_text().splitlines():
            m = re.match(r'^DONE\s+\S+\s+\[(.+)\]', line)
            if m:
                done_words.add(m.group(1).strip())

    pending = [w for w in words if w not in done_words]
    if not pending:
        print(f"All {len(words)} words already done.")
        return

    print(f"Queue: {len(words)} words. Pending: {len(pending)}. Batch size: {args.batch_size}")

    next_num = get_next_file_num(phase)
    fmt = FILE_NUM_FORMAT[phase]

    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    batch_num = 0
    i = 0
    while i < len(pending):
        batch = pending[i:i + args.batch_size]
        file_map = {}
        for j, word in enumerate(batch):
            num = next_num + i + j
            fname = f"phase_{phase}/phase_{phase}_{num:{fmt}}.md"
            file_map[word] = fname

        prompt_text = build_prompt(phase, pos, batch, file_map)
        prompt_file = PROMPTS_DIR / f"phase_{phase}_{pos}_{batch_num:03d}.txt"
        prompt_file.write_text(prompt_text)
        print(f"  Wrote {prompt_file.name} ({len(batch)} words: {batch[0]}..{batch[-1]})")

        batch_num += 1
        i += args.batch_size

    print(f"\nGenerated {batch_num} prompt files in {PROMPTS_DIR}")
    print(f"Run: meta/scripts/opencode_ds_fanout.sh --workers 10 tmp/backfill_prompts/phase_{phase}_{pos}_*.txt")
    print(f"Then: python3 meta/scripts/parse_backfill_output.py --phase {phase} --pos {pos}")


if __name__ == "__main__":
    main()
