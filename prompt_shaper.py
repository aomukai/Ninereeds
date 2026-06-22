"""Prompt shaping layer for BDH.

Converts a user's natural-language request into a completion-friendly prompt
that a raw language model (non-instruction-tuned) can handle well.

The model completes text — it does not answer instructions.
Every shape here gives the model a running start in the right register.
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# Shape definitions
# ---------------------------------------------------------------------------

def shape_qa(prompt: str) -> str:
    """Q: ...\nA:  — works when the model saw Q&A text in training."""
    return f"Q: {prompt.rstrip('?')}?\nA:"


def shape_definition(subject: str) -> str:
    """Subject is ...  — factual/encyclopedic register."""
    return f"{subject} is"


def shape_story(prompt: str) -> str:
    """Narrative register — model continues a story opening."""
    return prompt  # story starters are already good completion prompts


def shape_fill(prompt: str) -> str:
    """Ensures the prompt ends with a space so the model appends cleanly."""
    return prompt.rstrip() + " "


# ---------------------------------------------------------------------------
# Auto-shaper: picks a shape based on the input
# ---------------------------------------------------------------------------

_QUESTION_WORDS = re.compile(
    r"^\s*(what|who|why|when|where|how|is|are|do|does|can|could|would|should)\b",
    re.IGNORECASE,
)

_DEFINITION_PATTERN = re.compile(
    r"^\s*what\s+is\s+(?:a\s+|an\s+)?(.+?)\??\s*$",
    re.IGNORECASE,
)

_STORY_STARTERS = re.compile(
    r"^\s*(once upon|it was|she|he|they|the\s+\w+\s+(was|walked|opened|sat|ran|looked))",
    re.IGNORECASE,
)

# Prompts that are already perfect completion starters — don't touch them
_PASS_THROUGH = re.compile(
    r"^\s*(once upon|it was a)",
    re.IGNORECASE,
)


def shape(prompt: str) -> tuple[str, str]:
    """Return (shaped_prompt, shape_name).

    Tries shapes in order of specificity.
    """
    prompt = prompt.strip()

    # "Once upon a time..." — already ideal, return exactly as-is (no trailing space)
    if _PASS_THROUGH.match(prompt):
        return prompt, "passthrough"

    # "What is a X?" → "A X is"
    m = _DEFINITION_PATTERN.match(prompt)
    if m:
        subject = m.group(1).strip()
        article = "An" if subject[0].lower() in "aeiou" else "A"
        return f"{article} {subject} is", "definition"

    # Story-like opening → pass through with trailing space
    if _STORY_STARTERS.match(prompt):
        return shape_fill(prompt), "story"

    # Any other question → Q:/A: format
    if _QUESTION_WORDS.match(prompt) or prompt.endswith("?"):
        return shape_qa(prompt), "qa"

    # Incomplete sentence / statement → fill
    return shape_fill(prompt), "fill"


# ---------------------------------------------------------------------------
# Multilingual shape helpers
# ---------------------------------------------------------------------------

def shape_definition_de(noun_phrase: str) -> str:
    """German definition starter. Pass the full noun phrase incl. article.
    e.g. 'ein Buch' → 'Ein Buch ist'
    """
    cap = noun_phrase[0].upper() + noun_phrase[1:]
    return f"{cap} ist"


def shape_definition_jp(subject: str) -> str:
    """Japanese definition starter: '{subject}は'."""
    return f"{subject}は"


def shape_definition_zh(subject: str) -> str:
    """Chinese definition starter: '{subject}是'."""
    return f"{subject}是"


def shape_for(prompt: str, lang: str = "en") -> tuple[str, str]:
    """Shape a prompt for a given language. Returns (shaped_prompt, shape_name).

    For EN, delegates to the existing auto-shape() function.
    For DE/JP/ZH, applies language-specific definition patterns; falls back to
    Q:/A: for questions and fill for everything else.
    """
    if lang == "en":
        return shape(prompt)

    prompt = prompt.strip()

    if lang == "de":
        m = re.match(r"^\s*Was ist (ein(?:e|er|em|en)?\s+.+?)\??\s*$", prompt, re.IGNORECASE)
        if m:
            return shape_definition_de(m.group(1).strip()), "definition"
    elif lang == "jp":
        m = re.match(r"^(.+?)とは何ですか", prompt)
        if m:
            return shape_definition_jp(m.group(1)), "definition"
        m = re.match(r"^(.+?)は何ですか", prompt)
        if m:
            return shape_definition_jp(m.group(1)), "definition"
    elif lang == "zh":
        m = re.match(r"^(.+?)是什么", prompt)
        if m:
            return shape_definition_zh(m.group(1)), "definition"

    if prompt.endswith("?") or prompt.endswith("？"):
        return f"Q: {prompt}\nA:", "qa"

    return prompt.rstrip() + " ", "fill"


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        "What is a book?",
        "What is an ocean?",
        "Why do birds sing?",
        "She opened the door and saw",
        "Once upon a time there was a",
        "I am hungry because",
        "The weather today is",
        "How does a rainbow form?",
    ]
    for t in tests:
        shaped, name = shape(t)
        print(f"[{name:10s}] {t!r}")
        print(f"           → {shaped!r}")
        print()
