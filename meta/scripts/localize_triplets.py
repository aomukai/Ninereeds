#!/usr/bin/env python3
"""
localize_triplets.py - Generate DE/JP/ZH monolingual localizations of triplet stories.

Source:  training_data/triplet_stories/tier_N/*_EN.md
Output:  training_data/triplet_stories/tier_N/*_DE.md, *_JP.md, *_ZH.md

Usage:
  python3 meta/scripts/localize_triplets.py gen [--workers 8] [--batch 15] [--lang DE,JP,ZH] [--dry-run]
  python3 meta/scripts/localize_triplets.py report
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
TRIPLET_DIR = ROOT / "training_data" / "triplet_stories"
MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_BATCH = 15
DEFAULT_WORKERS = 8
ALL_LANGS = ["DE", "JP", "ZH"]

LANG_SPECS = {
    "DE": {
        "name": "German",
        "register": (
            "Register — German:\n"
            "- Natural narrative German, like a story in a German school reader (Lesebuch).\n"
            "- Flowing sentences. Präteritum or Perfekt for past events — both fine.\n"
            "- [user] turn: natural casual question in Du-form.\n"
            "- [Ninereeds] turn: flowing narrative. Not academic, not stiff.\n"
            "- Example Ninereeds tone:\n"
            "  Ein Kind pflanzte einen Samen in die Erde. Jeden Tag goss es ihn.\n"
            "  Nach einer Woche brach ein Trieb durch den Boden. Das Kind beobachtete, wie er wuchs.\n"
        ),
    },
    "JP": {
        "name": "Japanese",
        "register": (
            "Register — Japanese:\n"
            "- Plain past tense (〜た) throughout. No ですます anywhere.\n"
            "- Short, natural sentences. Light and flowing — not stiff or academic.\n"
            "- [user] turn: casual or natural question.\n"
            "- [Ninereeds] turn: flowing story in plain past tense.\n"
            "- Example Ninereeds tone:\n"
            "  子供が庭に種を植えた。毎日水をあげた。一週間後、芽が土から出てきた。子供はそれを見守った。\n"
            "- No romaji anywhere. Use correct counters.\n"
        ),
    },
    "ZH": {
        "name": "Traditional Chinese",
        "register": (
            "Register — Traditional Chinese (繁體中文):\n"
            "- Natural narrative Traditional Chinese. No spoken particles (啊、嘛、吧、呢).\n"
            "- [user] turn: natural question in written Chinese.\n"
            "- [Ninereeds] turn: clear, flowing narrative.\n"
            "- Example Ninereeds tone:\n"
            "  一個孩子在院子裡種下了種子。每天澆水。一週後，嫩芽從土裡冒出來。孩子靜靜地看著它生長。\n"
        ),
    },
}

STRUCTURAL_RULES = """
Rules:
- Keep [user] and [Ninereeds] tags exactly as written — same capitalization, no changes.
- Localize naturally: meaning-faithful and fluent, not word-for-word.
- Do NOT add explanations, summaries, or change the story's meaning.
- Each story is exactly two lines: the [user] line and the [Ninereeds] line.
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


def out_path(src: Path, lang: str) -> Path:
    return src.parent / src.name.replace("_EN.md", f"_{lang}.md")


def build_prompt(lang_code: str, stories: list[str], extra: str = "") -> str:
    spec = LANG_SPECS[lang_code]
    block = "\n\n".join(f"--- {i+1} ---\n{s}" for i, s in enumerate(stories))
    return (
        f"You are localizing short English stories into {spec['name']}.\n\n"
        f"{spec['register']}\n"
        f"{STRUCTURAL_RULES}\n"
        + (f"{extra}\n\n" if extra else "")
        + f"Localize each story below into {spec['name']}. "
        "Return them in the same numbered format (--- 1 ---, --- 2 ---, etc.). "
        "Output ONLY the localized stories — no preamble, no explanation.\n\n"
        f"{block}"
    )


def parse_response(text: str, n: int) -> list[str] | None:
    parts = re.split(r'-{2,}\s*\d+\s*-{2,}', text)
    contents = [p.strip() for p in parts[1:]]
    return contents if len(contents) == n else None


def validate_story(content: str) -> list[str]:
    errors = []
    if content.count("[user]") != 1:
        errors.append(f"[user] count={content.count('[user]')}")
    if content.count("[Ninereeds]") != 1:
        errors.append(f"[Ninereeds] count={content.count('[Ninereeds]')}")
    return errors


def process_batch(
    items: list[tuple[Path, str]],
    lang: str,
    client: OpenAI,
    dry_run: bool,
) -> list[str]:
    results = {}
    pending = []

    for src, content in items:
        op = out_path(src, lang)
        stem = op.stem
        if op.exists():
            results[stem] = f"  SKIP {stem} — exists"
        elif dry_run:
            results[stem] = f"  WOULD WRITE {op.name}  ({len(content)} chars)"
        else:
            pending.append((src, content, op, stem))

    if not pending:
        return [results[out_path(src, lang).stem] for src, _ in items]

    srcs_pending = [content for _, content, _, _ in pending]
    extra = ""

    for attempt in range(1, 3):
        prompt = build_prompt(lang, srcs_pending, extra)
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                max_tokens=32768,
                messages=[{"role": "user", "content": prompt}],
            )
            output = resp.choices[0].message.content.strip()
        except Exception as e:
            for _, _, _, stem in pending:
                results[stem] = f"  ERROR {stem}: {e}"
            break

        parsed = parse_response(output, len(pending))
        if parsed is None:
            got = len(re.split(r'-{2,}\s*\d+\s*-{2,}', output)) - 1
            if attempt == 1:
                extra = (
                    f"PREVIOUS ATTEMPT RETURNED {got} stories instead of {len(pending)}. "
                    f"You MUST return exactly {len(pending)} numbered stories."
                )
                continue
            for _, _, _, stem in pending:
                results[stem] = f"  FAIL {stem}: got {got} stories, expected {len(pending)}"
            break

        retry = []
        for (src, content, op, stem), localized in zip(pending, parsed):
            errs = validate_story(localized)
            if errs and attempt == 1:
                retry.append((src, content, op, stem))
            elif errs:
                results[stem] = f"  FAIL {stem}: {'; '.join(errs)}"
            else:
                op.write_text(localized + "\n", encoding="utf-8")
                results[stem] = f"  OK {op.name}  ({len(content)}→{len(localized)})"

        if not retry:
            break
        pending = retry
        srcs_pending = [content for _, content, _, _ in pending]
        extra = "PREVIOUS ATTEMPT HAD TAG ERRORS. Every story must start with [user] and contain [Ninereeds]."

    return [results.get(out_path(src, lang).stem, f"  MISSING {src.stem}") for src, _ in items]


def cmd_report():
    sources = sorted(TRIPLET_DIR.rglob("*_EN.md"))
    print(f"Source files: {len(sources)}")
    for lang in ALL_LANGS:
        done = sum(1 for s in sources if out_path(s, lang).exists())
        print(f"  {lang}: {done}/{len(sources)} ({len(sources)-done} remaining)")


def cmd_gen(args):
    dry_run = "--dry-run" in args
    workers = DEFAULT_WORKERS
    batch_size = DEFAULT_BATCH
    langs = ALL_LANGS[:]

    for i, a in enumerate(args):
        if a == "--workers" and i + 1 < len(args):
            workers = int(args[i + 1])
        elif a.startswith("--workers="):
            workers = int(a.split("=", 1)[1])
        elif a == "--batch" and i + 1 < len(args):
            batch_size = int(args[i + 1])
        elif a.startswith("--batch="):
            batch_size = int(a.split("=", 1)[1])
        elif a == "--lang" and i + 1 < len(args):
            langs = [x.strip().upper() for x in args[i + 1].split(",")]
        elif a.startswith("--lang="):
            langs = [x.strip().upper() for x in a.split("=", 1)[1].split(",")]

    if dry_run:
        print("(dry run — no files will be written)\n")

    api_key = get_api_key()
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    sources = sorted(TRIPLET_DIR.rglob("*_EN.md"))
    batches = [
        [(src, src.read_text(encoding="utf-8").rstrip()) for src in sources[i:i+batch_size]]
        for i in range(0, len(sources), batch_size)
    ]
    jobs = [(batch, lang) for lang in langs for batch in batches]

    print(f"Sources: {len(sources)} | Batch: {batch_size} | Batches: {len(batches)}")
    print(f"Languages: {langs} | Jobs: {len(jobs)} | Workers: {workers}\n")

    ok = fail = skip = 0
    lock = threading.Lock()

    def run(job):
        nonlocal ok, fail, skip
        batch, lang = job
        results = process_batch(batch, lang, client, dry_run)
        with lock:
            for r in results:
                print(r)
                if "OK" in r or "WOULD" in r:
                    ok += 1
                elif "SKIP" in r:
                    skip += 1
                else:
                    fail += 1

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(as_completed([ex.submit(run, j) for j in jobs]))

    print(f"\nDone: {ok} written, {skip} skipped, {fail} failed.")


def main():
    args = sys.argv[1:]
    if not args or args[0] == "report":
        cmd_report()
    elif args[0] == "gen":
        cmd_gen(args[1:])
    else:
        print("Usage: localize_triplets.py [gen|report] [options]")
        sys.exit(1)


if __name__ == "__main__":
    main()
