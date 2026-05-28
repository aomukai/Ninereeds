#!/usr/bin/env python3
"""
localize_wiki.py — Generate DE/JP/ZH monolingual localizations of wiki files.

Source:  training_data/wiki/level_N/topic/NNN_word_EN.md
Output:  training_data/wiki/level_N/topic/NNN_word_DE.md
         training_data/wiki/level_N/topic/NNN_word_JP.md
         training_data/wiki/level_N/topic/NNN_word_ZH.md

Cross-platform: reads OPENROUTER_API_KEY (or OPENAI_API_KEY). No opencode needed.

Usage:
  python3 meta/scripts/localize_wiki.py gen [--level 1] [--lang JP,ZH] [--workers 6]
  python3 meta/scripts/localize_wiki.py gen --level all --batch 10 --workers 8
  python3 meta/scripts/localize_wiki.py report [--level 1]
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent.parent

_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

WIKI_ROOT = ROOT / "training_data" / "wiki"
MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_BATCH = 10
DEFAULT_WORKERS = 6
ALL_LANGS = ["DE", "JP", "ZH"]
ALL_LEVELS = ["level_1", "level_2", "level_3", "level_4"]


# ── Language specs ─────────────────────────────────────────────────────────────

LANG_SPECS = {
    "DE": {
        "name": "German",
        "register": (
            "Register — German:\n"
            "- Clear, simple Schulbuch style. Complete sentences.\n"
            "- [user] turn: natural German question — the phrasing a native speaker would use.\n"
            "- [Ninereeds] turn: express the meaning in natural German. Do NOT translate word-for-word.\n"
            "  Choose the German expression that carries the same MEANING, even if the words differ.\n"
            "- Do NOT use pronouns (er, sie, es, ihn, ihm, sein, ihr, etc.) — repeat the noun instead.\n"
            "- German articles: der/die/das/ein/eine — use correct gender.\n"
        ),
    },
    "JP": {
        "name": "Japanese",
        "register": (
            "Register — Japanese:\n"
            "- Plain form (だ/である style). No ですます form anywhere.\n"
            "- [user] turn: natural Japanese question — the phrasing a native speaker would use.\n"
            "- [Ninereeds] turn: express each idea in natural Japanese. Do NOT translate word-for-word.\n"
            "  Choose the Japanese expression that carries the same MEANING, even if the words differ.\n"
            "- CRITICAL — animate/inanimate verbs: inanimate objects do NOT sit (座る), land (着地する),\n"
            "  or perform human actions. Use ある for existence/location, 生える for growth, 落ちる for\n"
            "  falling, etc.\n"
            "  BAD: 石が地面に座っている  GOOD: 石が地面にある\n"
            "  BAD: 葉が地面に着地する  GOOD: 葉が地面に落ちる\n"
            "- CRITICAL — no possession calques: do NOT use 持つ for attributes of inanimate objects.\n"
            "  BAD: 机は四本の足を持つ  GOOD: 机には四本の足がある\n"
            "- Do NOT use pronouns (それ、その、彼、彼女、etc.) — repeat the noun instead.\n"
            "- No romaji. Use correct counters. Short, natural sentences.\n"
        ),
    },
    "ZH": {
        "name": "Traditional Chinese",
        "register": (
            "Register — Traditional Chinese (繁體中文):\n"
            "- TRADITIONAL characters ONLY. Never use Simplified Chinese characters.\n"
            "- [user] turn: natural written Traditional Chinese question — the phrasing a native speaker would use.\n"
            "- [Ninereeds] turn: express each idea in natural Traditional Chinese. Do NOT translate word-for-word.\n"
            "  Choose the Chinese expression that carries the same MEANING, even if the words differ.\n"
            "- CRITICAL — animate/inanimate verbs: inanimate objects do NOT sit (坐), land (著陸/降落),\n"
            "  or perform human actions. Use 在 for location, 生長 for growth, 落下 for falling, etc.\n"
            "  BAD: 橡實坐在泥土上  GOOD: 橡實在泥土上\n"
            "  BAD: 橡實著陸在地面  GOOD: 橡實落在地面上\n"
            "- CRITICAL — no possession calques: do NOT translate 'has' as 持有/擁有 for physical attributes.\n"
            "  BAD: 桌子擁有四條腿  GOOD: 桌子有四條腿\n"
            "- Do NOT use pronouns (它、牠、他、她、其、etc.) — repeat the noun instead.\n"
            "- Complete sentences. Standard written register.\n"
        ),
    },
}

STRUCTURAL_RULES = """\
Structural rules (apply to ALL languages):
- Keep [user] and [Ninereeds] tags EXACTLY as written — same capitalisation, no changes.
- The file has exactly one [user] line and one [Ninereeds] line.
- The [Ninereeds] tag and the localized response are on the SAME line: [Ninereeds]Response here.
- Do NOT split the [Ninereeds] response across multiple lines.
- Do NOT add extra lines, headings, or explanatory text.
- Output ONLY the localized file content — no preamble, no explanation.
"""


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_client() -> OpenAI:
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        auth = Path.home() / ".local/share/opencode/auth.json"
        if auth.exists():
            try:
                key = json.loads(auth.read_text()).get("openrouter", {}).get("key")
            except Exception:
                pass
    if not key:
        sys.exit("Set OPENROUTER_API_KEY or OPENAI_API_KEY before running.")
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)


def out_path(src: Path, lang: str) -> Path:
    return src.parent / src.name.replace("_EN.md", f"_{lang}.md")


def is_source(path: Path) -> bool:
    return path.name.endswith("_EN.md")


def count_tag(text: str, tag: str) -> int:
    return len(re.findall(rf"^\[{re.escape(tag)}\]", text, re.MULTILINE))


def validate_localized(source: str, output: str, lang: str) -> list[str]:
    errors: list[str] = []
    if count_tag(output, "user") != count_tag(source, "user"):
        errors.append(f"[user] count mismatch")
    if count_tag(output, "Ninereeds") != count_tag(source, "Ninereeds"):
        errors.append(f"[Ninereeds] count mismatch")
    # Exclude --- separators; for multi-paragraph responses, only require
    # at least one line per [user]/[Ninereeds] tag (languages like ZH
    # legitimately compress multi-paragraph EN responses into fewer lines).
    src_lines = [l for l in source.splitlines() if l.strip() and l.strip() != "---"]
    out_lines = [l for l in output.splitlines() if l.strip() and l.strip() != "---"]
    n_tags = count_tag(source, "user") + count_tag(source, "Ninereeds")
    if len(out_lines) < n_tags:
        errors.append(f"line count {len(out_lines)} ≠ source {len(src_lines)}")
    if lang == "ZH":
        simplified_sample = "给苹玛铅篮邻个来说为国"
        if any(ch in output for ch in simplified_sample):
            errors.append("Simplified Chinese found — must be Traditional")
    if lang == "JP" and not re.search(r"[぀-ヿ]", output):
        errors.append("No Japanese characters found")
    return errors


def build_prompt(lang: str, files: list[str]) -> str:
    spec = LANG_SPECS[lang]
    numbered = "\n\n".join(f"--- {i + 1} ---\n{content}" for i, content in enumerate(files))
    return (
        f"You are localizing Ninereeds training files into {spec['name']}.\n"
        "Ninereeds is a small AI. Each file is a [user]/[Ninereeds] dialogue entry.\n\n"
        "CORE PRINCIPLE: localize naturally. A native speaker must not be able to tell this came from English.\n"
        "Do NOT translate word-for-word. Express the MEANING in the most natural way for the target language.\n\n"
        f"{spec['register']}\n"
        f"{STRUCTURAL_RULES}\n"
        f"Localize each file below into {spec['name']}. "
        f"Return them in the same numbered format (--- 1 ---, --- 2 ---, etc.). "
        "Output ONLY the localized file contents — no preamble, no explanation.\n\n"
        f"{numbered}"
    )


def parse_response(text: str, n: int) -> list[str] | None:
    parts = re.split(r"-{2,}\s*\d+\s*-{2,}", text)
    contents = [p.strip() for p in parts[1:]]
    return contents if len(contents) == n else None


# ── Core processing ────────────────────────────────────────────────────────────

def process_batch(
    items: list[tuple[Path, str]],
    lang: str,
    client: OpenAI,
    dry_run: bool,
) -> list[str]:
    results: dict[str, str] = {}
    pending: list[tuple[Path, str, Path]] = []

    for src, content in items:
        dest = out_path(src, lang)
        key = src.name
        if dest.exists():
            results[key] = f"  SKIP {src.relative_to(WIKI_ROOT)}"
        elif dry_run:
            results[key] = f"  WOULD WRITE {dest.relative_to(WIKI_ROOT)}"
        else:
            pending.append((src, content, dest))

    if not pending:
        return [results[src.name] for src, _ in items]

    pending_contents = [c for _, c, _ in pending]
    extra_hint = ""

    for attempt in range(1, 3):
        prompt = build_prompt(lang, pending_contents)
        if extra_hint:
            prompt = extra_hint + "\n\n" + prompt

        try:
            resp = client.chat.completions.create(
                model=MODEL,
                max_tokens=32768,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            for src, _, _ in pending:
                results[src.name] = f"  ERROR {src.name}: {exc}"
            break

        parsed = parse_response(raw, len(pending))
        if parsed is None:
            got = len(re.split(r"-{2,}\s*\d+\s*-{2,}", raw)) - 1
            if attempt == 1:
                extra_hint = (
                    f"PREVIOUS ATTEMPT RETURNED {got} files instead of {len(pending)}. "
                    f"You MUST return exactly {len(pending)} numbered blocks."
                )
                continue
            for src, _, _ in pending:
                results[src.name] = f"  FAIL {src.name}: parse error — got {got}, expected {len(pending)}"
            break

        retry: list[tuple[Path, str, Path]] = []
        for (src, content, dest), localized in zip(pending, parsed):
            errs = validate_localized(content, localized, lang)
            if errs and attempt == 1:
                retry.append((src, content, dest))
            elif errs:
                results[src.name] = f"  FAIL {src.name} [{lang}]: {'; '.join(errs)}"
            else:
                dest.write_text(localized + "\n", encoding="utf-8")
                results[src.name] = f"  OK   {dest.relative_to(WIKI_ROOT)}"

        if not retry:
            break
        pending = retry
        pending_contents = [c for _, c, _ in pending]
        extra_hint = (
            "PREVIOUS ATTEMPT HAD VALIDATION ERRORS. "
            "Match [user]/[Ninereeds] structure exactly. "
            "Keep [Ninereeds] response on a single line. "
            "Do NOT use Simplified Chinese."
        )

    return [results.get(src.name, f"  MISSING {src.name}") for src, _ in items]


# ── Source collection ──────────────────────────────────────────────────────────

def collect_sources(levels: list[str], lang: str) -> list[tuple[Path, str]]:
    jobs: list[tuple[Path, str]] = []
    for level in levels:
        level_dir = WIKI_ROOT / level
        if not level_dir.exists():
            continue
        for src in sorted(level_dir.rglob("*_EN.md")):
            if not is_source(src):
                continue
            if out_path(src, lang).exists():
                continue
            jobs.append((src, src.read_text(encoding="utf-8").rstrip()))
    return jobs


# ── Commands ───────────────────────────────────────────────────────────────────

def cmd_report(levels: list[str]) -> None:
    total_src = 0
    total_done: dict[str, int] = {lang: 0 for lang in ALL_LANGS}

    for level in levels:
        level_dir = WIKI_ROOT / level
        if not level_dir.exists():
            continue
        src_files = sorted(level_dir.rglob("*_EN.md"))
        n = len(src_files)
        total_src += n
        print(f"\n{level}  ({n} source files)")
        for lang in ALL_LANGS:
            done = sum(1 for f in src_files if out_path(f, lang).exists())
            total_done[lang] += done
            pct = 100 * done // n if n else 0
            bar = "█" * (done * 20 // n) + "░" * (20 - done * 20 // n) if n else ""
            print(f"  {lang}  {done:4d}/{n}  {pct:3d}%  {bar}")

    if len(levels) > 1:
        print(f"\nTotal source files: {total_src}")
        for lang in ALL_LANGS:
            d = total_done[lang]
            pct = 100 * d // total_src if total_src else 0
            print(f"  {lang}  {d:5d}/{total_src}  {pct}%")


def cmd_gen(
    levels: list[str],
    langs: list[str],
    batch_size: int,
    workers: int,
    dry_run: bool,
) -> None:
    if dry_run:
        print("DRY RUN — no files will be written\n")

    client = None if dry_run else get_client()

    for lang in langs:
        jobs = collect_sources(levels, lang)
        if not jobs:
            print(f"[{lang}] Nothing to do.")
            continue

        batches = [jobs[i: i + batch_size] for i in range(0, len(jobs), batch_size)]
        print(f"[{lang}] {len(jobs)} files  batch={batch_size}  batches={len(batches)}  workers={workers}", flush=True)

        ok = fail = skip = 0
        lock = threading.Lock()

        def run_batch(batch: list[tuple[Path, str]], _lang: str = lang) -> None:
            nonlocal ok, fail, skip
            lines = process_batch(batch, _lang, client, dry_run)
            with lock:
                for line in lines:
                    print(line, flush=True)
                    if "OK" in line or "WOULD" in line:
                        ok += 1
                    elif "SKIP" in line:
                        skip += 1
                    else:
                        fail += 1

        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(as_completed([pool.submit(run_batch, b) for b in batches]))

        print(f"[{lang}] done: {ok} written, {skip} skipped, {fail} failed.\n", flush=True)


# ── Entry point ────────────────────────────────────────────────────────────────

def parse_args() -> tuple[str, dict]:
    args = sys.argv[1:]
    cmd = args[0] if args else "report"
    opts: dict = {
        "levels": ALL_LEVELS[:],
        "langs": ALL_LANGS[:],
        "batch": DEFAULT_BATCH,
        "workers": DEFAULT_WORKERS,
        "dry_run": "--dry-run" in args,
    }

    i = 1
    while i < len(args):
        a = args[i]
        def nxt() -> str:
            nonlocal i; i += 1; return args[i]
        if a in ("--level", "--levels"):
            v = nxt()
            opts["levels"] = ALL_LEVELS if v == "all" else [f"level_{v}"]
        elif a == "--lang":
            opts["langs"] = [x.strip().upper() for x in nxt().split(",")]
        elif a == "--batch":
            opts["batch"] = int(nxt())
        elif a == "--workers":
            opts["workers"] = int(nxt())
        elif a.startswith("--level="):
            v = a.split("=", 1)[1]
            opts["levels"] = ALL_LEVELS if v == "all" else [f"level_{v}"]
        elif a.startswith("--lang="):
            opts["langs"] = [x.strip().upper() for x in a.split("=", 1)[1].split(",")]
        elif a.startswith("--batch="):
            opts["batch"] = int(a.split("=", 1)[1])
        elif a.startswith("--workers="):
            opts["workers"] = int(a.split("=", 1)[1])
        i += 1

    return cmd, opts


def main() -> None:
    cmd, opts = parse_args()
    if cmd == "report":
        cmd_report(opts["levels"])
    elif cmd == "gen":
        cmd_gen(
            levels=opts["levels"],
            langs=opts["langs"],
            batch_size=opts["batch"],
            workers=opts["workers"],
            dry_run=opts["dry_run"],
        )
    else:
        sys.exit(f"Unknown command: {cmd!r}  (use 'gen' or 'report')")


if __name__ == "__main__":
    main()
