#!/usr/bin/env python3
"""
localize_reasoning.py - Generate DE/JP/ZH monolingual localizations of reasoning files.

Source:  training_data/reasoning/*.md  (no language suffix = EN)
Output:  training_data/reasoning/*_DE.md, *_JP.md, *_ZH.md

Usage:
  python3 meta/scripts/localize_reasoning.py [--workers N] [--dry-run] [--lang DE,JP,ZH]
"""

import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent.parent
REASONING_DIR = ROOT / "training_data" / "reasoning"
MODEL = "deepseek/deepseek-v4-flash"

LANG_SPECS = {
    "DE": {
        "name": "German",
        "register": (
            "Register — German textbook style (Schulbuch):\n"
            "- Precise and clear, like a German school textbook. Not academic, not casual.\n"
            "- Du-form is acceptable in [user] turns.\n"
            "- [Ninereeds] turns: clear declarative sentences. No colloquialisms.\n"
            "- Tone example: \"Eins plus eins ergibt zwei. "
            "Das bedeutet, dass eine Einheit mit einer weiteren Einheit zusammengefasst "
            "zwei Einheiten ergibt.\"\n"
        ),
    },
    "JP": {
        "name": "Japanese",
        "register": (
            "Register — Japanese:\n"
            "- Use plain form (常体) throughout. No ですます anywhere.\n"
            "- Light and natural: short sentences, active voice, simple everyday verbs.\n"
            "  AVOID: heavy academic forms — 〜のである、〜されたため、〜増加した、〜において\n"
            "  PREFER: natural plain forms — 〜なので、〜増えた、〜加わった、〜だから\n"
            "- [Ninereeds] turns: reasoning should flow like clear thinking, not academic prose.\n"
            "  Target tone:\n"
            "    最初に5枚の硬貨があった。\n"
            "    硬貨を広げると見た目は変わるが、硬貨の数は変わらない。\n"
            "    硬貨を追加したり取り除いたりしていない。\n"
            "    したがって、まだ5枚である。\n"
            "- [user] turns: natural and conversational. Casual or polite, both fine.\n"
            "- No romaji anywhere.\n"
            "- Use correct Japanese counters: 匹 (small animals, worms, fish), 羽 (birds),\n"
            "  個 (round/generic objects), 本 (long thin objects), 枚 (flat/coin objects),\n"
            "  人 (people), 冊 (books), 台 (machines), 杯 (cups/bowls).\n"
        ),
    },
    "ZH": {
        "name": "Traditional Chinese",
        "register": (
            "Register — Traditional Chinese (繁體中文):\n"
            "- Use Traditional Chinese throughout.\n"
            "- Standard Written Chinese (書面語): clear, precise.\n"
            "- No spoken particles: 啊、嘛、吧、呢 are forbidden in both turns.\n"
            "- Prefer formal connectives: 因此、然而、此外、即 over 所以、但是.\n"
            "- Tone example: 一加一等於二。這表示將一個單位與另一個單位合併，總數變為二。\n"
        ),
    },
}

STRUCTURAL_RULES = """
Structural rules — follow exactly:
- Keep all tags exactly as written: [user] and [Ninereeds]. Do not alter capitalization or spacing.
- Keep all blank lines where they appear in the source.
- Keep all mathematical expressions exactly: 1 + 1 = 2, X + 3, A = 5, etc. Do not rewrite or reformat them.
- Translate section header labels (Symbolic Mode:, Verbal Mode:, Grounded Story Mode:, Reasoning Chain:) naturally into the target language.
- Lines beginning with # are file metadata — translate them into the target language.
- Separators (---) stay as-is.
"""

SEMANTIC_RULES = """
Semantic preservation — this is critical:
- Every noun, animal, object, number, and actor-patient relationship must appear in the output.
- If the English says "a bird finds one worm", the output must have a bird finding a worm — not a bird finding another bird.
- Counts are exact: "three apples" must be three apples in the target language.
- Do NOT substitute objects or animals. Do NOT shift who does what to whom.
- For math story problems: the scenario (who has what, what they do) must be identical to the English.
"""


def get_api_key():
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        auth = Path.home() / ".local/share/opencode/auth.json"
        if auth.exists():
            data = json.loads(auth.read_text())
            key = data.get("openrouter", {}).get("key")
    if not key:
        raise RuntimeError("No API key found. Set OPENROUTER_API_KEY.")
    return key


def build_prompt(lang_code: str, source_text: str, extra: str = "") -> str:
    spec = LANG_SPECS[lang_code]
    return (
        f"You are localizing English AI training files into {spec['name']}.\n\n"
        f"{spec['register']}\n"
        f"{STRUCTURAL_RULES}\n"
        f"{SEMANTIC_RULES}\n"
        + (f"{extra}\n" if extra else "")
        + f"Translate the entire file below into {spec['name']}. "
        "Output ONLY the translated file content — no preamble, no explanation, "
        "no markdown fences.\n\n"
        "--- BEGIN SOURCE ---\n"
        f"{source_text}\n"
        "--- END SOURCE ---"
    )


def validate(source: str, output: str, lang_code: str) -> list[str]:
    errors = []

    src_user = source.count("[user]")
    out_user = output.count("[user]")
    if src_user != out_user:
        errors.append(f"[user] count: expected {src_user}, got {out_user}")

    src_nr = source.count("[Ninereeds]")
    out_nr = output.count("[Ninereeds]")
    if src_nr != out_nr:
        errors.append(f"[Ninereeds] count: expected {src_nr}, got {out_nr}")

    # Check standalone math equations (e.g. "1 + 1 = 2") are preserved verbatim
    equations = re.findall(r'\d[\d\s]*[+\-×÷*]\s*\d[\d\s]*=\s*\d+', source)
    for eq in equations:
        eq_norm = re.sub(r'\s+', ' ', eq).strip()
        if eq_norm not in output:
            errors.append(f"Math expression missing: {eq_norm!r}")

    return errors


def process_file(src: Path, lang_code: str, client: OpenAI, dry_run: bool) -> str:
    out_path = src.parent / f"{src.stem}_{lang_code}.md"
    if out_path.exists():
        return f"  SKIP {src.stem}_{lang_code} — exists"

    source_text = src.read_text(encoding="utf-8")
    if dry_run:
        return f"  WOULD WRITE {src.stem}_{lang_code}.md  ({len(source_text)} chars)"

    extra = ""

    for attempt in range(1, 3):
        prompt = build_prompt(lang_code, source_text, extra)
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                max_tokens=32768,
                messages=[{"role": "user", "content": prompt}],
            )
            output = resp.choices[0].message.content.strip()
        except Exception as e:
            return f"  ERROR {src.stem}_{lang_code}: {e}"

        errors = validate(source_text, output, lang_code)
        if errors:
            if attempt == 1:
                print(f"  VALIDATE FAIL (attempt 1) {src.stem}_{lang_code}:")
                for e in errors:
                    print(f"    {e}")
                extra = (
                    "PREVIOUS ATTEMPT HAD ERRORS — fix all of these:\n"
                    + "\n".join(f"- {e}" for e in errors)
                )
                continue
            return f"  FAIL {src.stem}_{lang_code}: {'; '.join(errors)}"

        if not dry_run:
            out_path.write_text(output + "\n", encoding="utf-8")
        return f"  OK {src.stem}_{lang_code}.md  ({len(source_text)}→{len(output)})"

    return f"  FAIL {src.stem}_{lang_code}: unknown"


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    workers = 3
    langs = ["DE", "JP", "ZH"]

    for i, a in enumerate(args):
        if a == "--workers" and i + 1 < len(args):
            workers = int(args[i + 1])
        elif a.startswith("--workers="):
            workers = int(a.split("=", 1)[1])
        elif a == "--lang" and i + 1 < len(args):
            langs = [x.strip().upper() for x in args[i + 1].split(",")]
        elif a.startswith("--lang="):
            langs = [x.strip().upper() for x in a.split("=", 1)[1].split(",")]

    if dry_run:
        print("(dry run — no files will be written)\n")

    api_key = get_api_key()
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    sources = sorted(
        f for f in REASONING_DIR.glob("*.md")
        if not re.search(r'_(DE|JP|ZH)\.md$', f.name)
    )
    jobs = [(src, lang) for src in sources for lang in langs]

    print(f"Localizing {len(sources)} reasoning files × {len(langs)} languages = {len(jobs)} jobs")
    print(f"Workers: {workers}\n")

    ok = fail = skip = 0
    lock = threading.Lock()

    def run(job):
        nonlocal ok, fail, skip
        result = process_file(job[0], job[1], client, dry_run)
        with lock:
            print(result)
            if "OK" in result:
                ok += 1
            elif "SKIP" in result:
                skip += 1
            else:
                fail += 1

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(as_completed([ex.submit(run, j) for j in jobs]))

    print(f"\nDone: {ok} written, {skip} skipped, {fail} failed.")


if __name__ == "__main__":
    main()
