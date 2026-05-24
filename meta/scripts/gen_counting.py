#!/usr/bin/env python3
"""
gen_counting.py — Generate counting curriculum files for training_data/reasoning/

9 number ranges × 4 languages = 36 files
  EN: generated algorithmically (no API)
  DE/JP/ZH: generated via DeepSeek

Usage:
  python3 meta/scripts/gen_counting.py [--dry-run] [--lang EN,DE,JP,ZH] [--workers N]
"""

import os
import re
import sys
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent.parent
REASONING_DIR = ROOT / "training_data" / "reasoning"
MODEL = "deepseek/deepseek-v4-flash"

# ── English number-to-words (0–9999) ──────────────────────────────────────────

_ONES = [
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen",
]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def n2w(n: int) -> str:
    """Integer 0–9999 → English words."""
    if n < 20:
        return _ONES[n]
    if n < 100:
        t = _TENS[n // 10]
        o = n % 10
        return t if o == 0 else f"{t}-{_ONES[o]}"
    if n < 1000:
        h = _ONES[n // 100]
        rest = n % 100
        if rest == 0:
            return f"{h} hundred"
        return f"{h} hundred and {n2w(rest)}"
    # 1000–9999
    th = _ONES[n // 1000]
    rest = n % 1000
    if rest == 0:
        return f"{th} thousand"
    if rest < 100:
        return f"{th} thousand and {n2w(rest)}"
    return f"{th} thousand {n2w(rest)}"


# ── Range definitions ─────────────────────────────────────────────────────────
# Entry types:
#   ("arith", prev, inc, curr)  →  "What's PREV plus INC? … PREV+INC=CURR"
#   ("recog", curr)             →  "How do you say CURR? …"

def _chain(start: int, end: int, step: int):
    entries = []
    prev = start - step
    n = start
    while n <= end:
        entries.append(("arith", prev, step, n))
        prev = n
        n += step
    return entries


def _recog(*nums):
    return [("recog", n) for n in nums]


RANGES = {
    "1_30":     _chain(1, 30, 1),
    "40_100":   _chain(40, 100, 10),
    "110_200":  _chain(110, 200, 10),
    "300_1000": _chain(300, 1000, 100),
    "1001_1040": [
        ("arith", 1000, 1,  1001),
        ("arith", 1001, 1,  1002),
        ("arith", 1002, 10, 1012),
        ("arith", 1012, 8,  1020),
        ("arith", 1020, 10, 1030),
        ("arith", 1030, 10, 1040),
    ],
    "1100_2000": [
        ("arith", 1000, 100,  1100),
        ("arith", 1100, 100,  1200),
        ("arith", 1200, 100,  1300),
        ("arith", 1000, 1000, 2000),
    ],
    "2020_3000": [
        ("recog", 2020),
        ("recog", 2050),
        ("arith", 2000, 1000, 3000),
    ],
    "4000_9000": _chain(4000, 9000, 1000),
    "9001_9999": _recog(9001, 9010, 9100, 9999),
}

RANGE_ORDER = [
    "1_30", "40_100", "110_200", "300_1000",
    "1001_1040", "1100_2000", "2020_3000", "4000_9000", "9001_9999",
]

# ── EN content builder ────────────────────────────────────────────────────────

def _arith_block_en(prev: int, inc: int, curr: int) -> str:
    pw = n2w(prev)
    iw = n2w(inc)
    cw = n2w(curr)
    return (
        f"[user]What's {pw} plus {iw}?\n"
        f"[Ninereeds]{pw.capitalize()} plus {iw} is {cw}.\n"
        f"[user]How do you write that in numbers?\n"
        f"[Ninereeds]{prev}+{inc}={curr}"
    )


def _recog_block_en(curr: int) -> str:
    cw = n2w(curr)
    return (
        f"[user]How do you say {curr}?\n"
        f"[Ninereeds]{curr} is {cw}.\n"
        f"[user]How do you write \"{cw}\" in numbers?\n"
        f"[Ninereeds]{cw.capitalize()} is {curr}."
    )


def build_en_content(range_key: str) -> str:
    title = f"# Counting — {range_key.replace('_', ' to ')}"
    blocks = []
    for entry in RANGES[range_key]:
        if entry[0] == "arith":
            _, prev, inc, curr = entry
            blocks.append(_arith_block_en(prev, inc, curr))
        else:
            _, curr = entry
            blocks.append(_recog_block_en(curr))
    return title + "\n\n" + "\n\n".join(blocks) + "\n"


# ── DeepSeek localisation ─────────────────────────────────────────────────────

LANG_SPECS = {
    "DE": {
        "name": "German",
        "register": (
            "Register — German (Schulbuch style):\n"
            "- Clear, precise, like a German school textbook.\n"
            "- Du-form is fine in [user] turns.\n"
            "- [Ninereeds] turns: declarative sentences, no colloquialisms.\n"
            "- Use natural German number words: eins, zwei, drei ... zwanzig, dreißig, "
            "hundert, tausend, neuntausendneunhundertneunundneunzig.\n"
            "- Compounds without spaces where German requires them (dreiundzwanzig).\n"
        ),
    },
    "JP": {
        "name": "Japanese",
        "register": (
            "Register — Japanese (plain form, 常体):\n"
            "- Plain form throughout. No ですます.\n"
            "- Natural, light sentences. Avoid heavy academic forms.\n"
            "- Use kanji numerals where natural: 一、二、三、四、五 ... 千、九千九百九十九.\n"
            "- For [user] Q&A about counting: natural casual phrasing.\n"
            "- No romaji anywhere.\n"
        ),
    },
    "ZH": {
        "name": "Traditional Chinese",
        "register": (
            "Register — Traditional Chinese (繁體中文):\n"
            "- Traditional characters throughout.\n"
            "- Standard Written Chinese (書面語): clear, precise.\n"
            "- Use natural Chinese number words: 一、二、三、四 ... 九千九百九十九.\n"
            "- No spoken particles: 啊、嘛、吧、呢 are forbidden.\n"
        ),
    },
}

STRUCTURAL_RULES = """
Structural rules — follow exactly:
- Keep all tags exactly as written: [user] and [Ninereeds].
- Keep all blank lines where they appear in the source.
- Keep all arithmetic expressions exactly: 1+1=2, 30+10=40, 1000+1=1001, etc.
  Do NOT rewrite, reformat, or add spaces inside them.
- The # title line at the top: translate only the words after "# Counting — ".
- Output ONLY the file content. No preamble, no explanation, no markdown fences.
"""


def build_prompt(lang_code: str, source_text: str, extra: str = "") -> str:
    spec = LANG_SPECS[lang_code]
    return (
        f"You are localizing an English counting/arithmetic training file into {spec['name']}.\n\n"
        f"{spec['register']}\n"
        f"{STRUCTURAL_RULES}\n"
        + (f"{extra}\n" if extra else "")
        + f"Translate the entire file below into {spec['name']}. "
        "Output ONLY the translated file content.\n\n"
        "--- BEGIN SOURCE ---\n"
        f"{source_text}\n"
        "--- END SOURCE ---"
    )


def validate(source: str, output: str) -> list[str]:
    errors = []
    for tag in ("[user]", "[Ninereeds]"):
        s = source.count(tag)
        o = output.count(tag)
        if s != o:
            errors.append(f"{tag} count: expected {s}, got {o}")
    for eq in re.findall(r'\d+[+\-]\d+=\d+', source):
        if eq not in output:
            errors.append(f"Arithmetic expression missing: {eq!r}")
    return errors


def get_api_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        auth = Path.home() / ".local/share/opencode/auth.json"
        if auth.exists():
            data = json.loads(auth.read_text())
            key = data.get("openrouter", {}).get("key")
    if not key:
        raise RuntimeError("No API key found. Set OPENROUTER_API_KEY.")
    return key


def generate_localisation(range_key: str, lang_code: str, source: str,
                           client: OpenAI, dry_run: bool) -> str:
    stem = f"counting_{range_key}"
    out_path = REASONING_DIR / f"{stem}_{lang_code}.md"
    if out_path.exists():
        return f"  SKIP {stem}_{lang_code} — exists"
    if dry_run:
        return f"  WOULD WRITE {stem}_{lang_code}.md"

    extra = ""
    for attempt in range(1, 3):
        prompt = build_prompt(lang_code, source, extra)
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                max_tokens=16384,
                messages=[{"role": "user", "content": prompt}],
            )
            output = resp.choices[0].message.content.strip()
        except Exception as e:
            return f"  ERROR {stem}_{lang_code}: {e}"

        errors = validate(source, output)
        if errors:
            if attempt == 1:
                extra = (
                    "PREVIOUS ATTEMPT HAD ERRORS — fix all:\n"
                    + "\n".join(f"- {e}" for e in errors)
                )
                continue
            return f"  FAIL {stem}_{lang_code}: {'; '.join(errors)}"

        out_path.write_text(output + "\n", encoding="utf-8")
        return f"  OK {stem}_{lang_code}.md"

    return f"  FAIL {stem}_{lang_code}: unknown"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    workers = 3
    langs = ["EN", "DE", "JP", "ZH"]

    for i, a in enumerate(args):
        if a == "--workers" and i + 1 < len(args):
            workers = int(args[i + 1])
        elif a.startswith("--workers="):
            workers = int(a.split("=", 1)[1])
        elif a == "--lang" and i + 1 < len(args):
            langs = [x.strip().upper() for x in args[i + 1].split(",")]
        elif a.startswith("--lang="):
            langs = [x.strip().upper() for x in a.split("=", 1)[1].split(",")]

    client = None
    if any(l != "EN" for l in langs) and not dry_run:
        client = OpenAI(
            api_key=get_api_key(),
            base_url="https://openrouter.ai/api/v1",
        )

    print(f"Generating counting files — langs: {langs}  dry_run: {dry_run}")
    print(f"Output dir: {REASONING_DIR}\n")

    # EN: always synchronous (no API)
    if "EN" in langs:
        for rk in RANGE_ORDER:
            stem = f"counting_{rk}"
            out_path = REASONING_DIR / f"{stem}.md"
            if out_path.exists():
                print(f"  SKIP {stem}.md — exists")
                continue
            content = build_en_content(rk)
            if dry_run:
                lines = content.count("\n")
                print(f"  WOULD WRITE {stem}.md  ({lines} lines)")
            else:
                out_path.write_text(content, encoding="utf-8")
                print(f"  OK {stem}.md")

    # DE/JP/ZH: parallel via DeepSeek
    non_en = [l for l in langs if l != "EN"]
    if non_en:
        jobs = []
        for rk in RANGE_ORDER:
            en_path = REASONING_DIR / f"counting_{rk}.md"
            if not en_path.exists():
                print(f"  WARN EN source missing for {rk} — skipping localisation")
                continue
            source = en_path.read_text(encoding="utf-8")
            for lang in non_en:
                jobs.append((rk, lang, source))

        print(f"\nLocalising {len(jobs)} files with {workers} workers…\n")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(generate_localisation, rk, lang, src, client, dry_run): (rk, lang)
                for rk, lang, src in jobs
            }
            for fut in as_completed(futures):
                print(fut.result())

    print("\nDone.")


if __name__ == "__main__":
    main()
