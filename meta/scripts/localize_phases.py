#!/usr/bin/env python3
"""
localize_phases.py — Generate DE/JP/ZH monolingual localizations of phase corpus files.

Source:  training_data/phases/phase_N/word.md   (English [user]/[Ninereeds])
Output:  training_data/phases/phase_N/word_DE.md
         training_data/phases/phase_N/word_JP.md
         training_data/phases/phase_N/word_ZH.md

Cross-platform: reads OPENROUTER_API_KEY (or OPENAI_API_KEY). No opencode needed.

Usage:
  python3 meta/scripts/localize_phases.py gen [--phase 1] [--letter b] [--workers 4]
  python3 meta/scripts/localize_phases.py gen --phase 1 --letter s --prefix sa-sl
  python3 meta/scripts/localize_phases.py gen --phase all --lang DE
  python3 meta/scripts/localize_phases.py report [--phase 1]

Letter split for heavy letters (e.g. 's' has 250+ files in phase_1):
  python3 meta/scripts/localize_phases.py gen --phase 1 --letter s --prefix sa-sl --workers 4
  python3 meta/scripts/localize_phases.py gen --phase 1 --letter s --prefix sm-sz --workers 4
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
PHASES_ROOT = ROOT / "training_data" / "phases"

MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_BATCH = 5
DEFAULT_WORKERS = 4
ALL_LANGS = ["DE", "JP", "ZH"]
ALL_PHASES = [f"phase_{i}" for i in range(1, 7)]

# ── Language specs ────────────────────────────────────────────────────────────

LANG_SPECS = {
    "DE": {
        "name": "German",
        "register": (
            "Register — German:\n"
            "- Clear, simple Schulbuch style. Complete sentences throughout.\n"
            "- [user] turn: translate the question naturally into German.\n"
            "- [Ninereeds] turn: translate each body line into a complete German sentence.\n"
            "- The last [Ninereeds] line in each block is a summary combining two properties "
            "  — translate it as a single summary sentence.\n"
            "- Do NOT use pronouns (er, sie, es, ihn, ihm, sein, ihr, etc.) "
            "  — repeat the noun or name instead.\n"
            "- German articles: der/die/das/ein/eine — use correct gender. "
            "  If the noun gender is uncertain, use the neuter 'das' or rephrase.\n"
            "- No negation in body lines.\n"
        ),
    },
    "JP": {
        "name": "Japanese",
        "register": (
            "Register — Japanese:\n"
            "- Plain form (だ/である style). No ですます form anywhere.\n"
            "- [user] turn: translate the question naturally into Japanese, plain form.\n"
            "- [Ninereeds] turn: translate each body line into a complete Japanese sentence.\n"
            "- The last [Ninereeds] line in each block is a summary — translate as one summary sentence.\n"
            "- Do NOT use pronouns (それ、その、彼、彼女、etc.) — repeat the noun instead.\n"
            "- No romaji. Use correct counters. Short, natural sentences.\n"
            "- No negation in body lines.\n"
        ),
    },
    "ZH": {
        "name": "Traditional Chinese",
        "register": (
            "Register — Traditional Chinese (繁體中文):\n"
            "- TRADITIONAL characters ONLY. Never use Simplified Chinese characters.\n"
            "- [user] turn: translate the question naturally into written Traditional Chinese.\n"
            "- [Ninereeds] turn: translate each body line into a complete Chinese sentence.\n"
            "- The last [Ninereeds] line in each block is a summary — translate as one summary sentence.\n"
            "- Do NOT use pronouns (它、牠、他、她、其、etc.) — repeat the noun instead.\n"
            "- Complete sentences. Standard written register.\n"
            "- No negation in body lines.\n"
        ),
    },
}

STRUCTURAL_RULES = """\
Structural rules (apply to ALL languages):
- Keep [user] and [Ninereeds] tags EXACTLY as written — same capitalisation, no changes.
- Preserve the exact number of [user]/[Ninereeds] pairs from the source file.
- Each [Ninereeds] block must have the SAME NUMBER OF LINES as in the source.
  The source has 6 lines per [Ninereeds] block — your translation must also have 6 lines.
- ONE SENTENCE PER LINE. Do NOT combine multiple sentences onto a single line.
  Each translated sentence goes on its own line, exactly as in the source.
- The [Ninereeds] tag and the first translated sentence are on the SAME line:
    [Ninereeds]First sentence here.
    Second sentence here.
    Third sentence here.
    Fourth sentence here.
    Fifth sentence here.
    Sixth sentence here.
- Blank lines between blocks must be preserved exactly as in the source.
- Do not add extra lines, headings, or explanatory text.
- Output ONLY the translated file content — no preamble, no section headers.
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_client() -> OpenAI:
    key = (
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
    )
    if not key:
        # Linux fallback: opencode auth store
        auth = Path.home() / ".local/share/opencode/auth.json"
        if auth.exists():
            try:
                data = json.loads(auth.read_text())
                key = data.get("openrouter", {}).get("key")
            except Exception:
                pass
    if not key:
        sys.exit("Set OPENROUTER_API_KEY or OPENAI_API_KEY before running.")
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)


def out_path(src: Path, lang: str) -> Path:
    return src.parent / f"{src.stem}_{lang}.md"


def is_source(path: Path) -> bool:
    """True if this is an English source file, not an already-localised sibling."""
    return not path.stem.endswith(("_DE", "_JP", "_ZH"))


def build_prompt(lang: str, files: list[str]) -> str:
    spec = LANG_SPECS[lang]
    numbered = "\n\n".join(f"--- {i + 1} ---\n{content}" for i, content in enumerate(files))
    return (
        f"You are localizing Ninereeds training files into {spec['name']}.\n"
        "Ninereeds is a small AI. Each file is a structured [user]/[Ninereeds] dialogue. "
        "Quality is critical — every malformed file has outsized impact on training.\n\n"
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


def count_tag(text: str, tag: str) -> int:
    return len(re.findall(rf"^\[{re.escape(tag)}\]", text, re.MULTILINE))


def _block_line_counts(text: str) -> list[int]:
    """Return the non-blank line count for each [Ninereeds] block."""
    counts = []
    in_block = False
    current = 0
    for line in text.splitlines():
        if line.startswith("[Ninereeds]"):
            if in_block:
                counts.append(current)
            in_block = True
            current = 1
        elif line.startswith("[user]"):
            if in_block:
                counts.append(current)
                in_block = False
                current = 0
        elif in_block:
            if line.strip():
                current += 1
    if in_block:
        counts.append(current)
    return counts


def validate_localized(source: str, output: str, lang: str) -> list[str]:
    errors: list[str] = []
    src_user = count_tag(source, "user")
    src_nine = count_tag(source, "Ninereeds")
    out_user = count_tag(output, "user")
    out_nine = count_tag(output, "Ninereeds")
    if out_user != src_user:
        errors.append(f"[user] count {out_user} ≠ {src_user}")
    if out_nine != src_nine:
        errors.append(f"[Ninereeds] count {out_nine} ≠ {src_nine}")
    src_counts = _block_line_counts(source)
    out_counts = _block_line_counts(output)
    if src_counts != out_counts:
        errors.append(f"line counts per block {out_counts} ≠ source {src_counts}")
    if lang == "ZH":
        simplified_sample = "给苹玛铅篮邻个来说为国"
        if any(ch in output for ch in simplified_sample):
            errors.append("Simplified Chinese found — must be Traditional")
    if lang == "JP":
        if not re.search(r"[぀-ヿ]", output):
            errors.append("No Japanese characters found")
    return errors


# ── Core processing ───────────────────────────────────────────────────────────

def process_batch(
    items: list[tuple[Path, str]],   # [(src_path, src_content), ...]
    lang: str,
    client: OpenAI,
    dry_run: bool,
) -> list[str]:
    """
    Localize a batch of source files into one language.
    Returns a list of status-line strings (one per item).
    """
    results: dict[str, str] = {}
    pending: list[tuple[Path, str, Path, str]] = []   # (src, content, dest, key)

    for src, content in items:
        dest = out_path(src, lang)
        key = src.stem
        if dest.exists():
            results[key] = f"  SKIP {src.relative_to(PHASES_ROOT)} → {dest.name}"
        elif dry_run:
            results[key] = f"  WOULD WRITE {dest.relative_to(PHASES_ROOT)}"
        else:
            pending.append((src, content, dest, key))

    if not pending:
        return [results[src.stem] for src, _ in items]

    pending_contents = [content for _, content, _, _ in pending]
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
            for _, _, _, key in pending:
                results[key] = f"  ERROR {key}: {exc}"
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
            for _, _, _, key in pending:
                results[key] = (
                    f"  FAIL {key}: parse error — got {got} blocks, expected {len(pending)}"
                )
            break

        retry: list[tuple[Path, str, Path, str]] = []
        for (src, content, dest, key), localized in zip(pending, parsed):
            errs = validate_localized(content, localized, lang)
            if errs and attempt == 1:
                retry.append((src, content, dest, key))
            elif errs:
                results[key] = f"  FAIL {key} [{lang}]: {'; '.join(errs)}"
            else:
                dest.write_text(localized + "\n", encoding="utf-8")
                results[key] = f"  OK   {src.relative_to(PHASES_ROOT)} → {dest.name}"

        if not retry:
            break
        pending = retry
        pending_contents = [c for _, c, _, _ in pending]
        extra_hint = (
            "PREVIOUS ATTEMPT HAD VALIDATION ERRORS. "
            "Each [user]/[Ninereeds] pair count must match the source exactly. "
            "Do NOT use pronouns. Do NOT use Simplified Chinese."
        )

    return [results.get(src.stem, f"  MISSING {src.stem}") for src, _ in items]


# ── Source collection ─────────────────────────────────────────────────────────

def collect_sources(
    phases: list[str],
    letter: str | None,
    prefix: str | None,
    lang: str,
) -> list[tuple[Path, str]]:
    """
    Return (src_path, src_content) pairs that need a `lang` localization.
    Filtered by letter and optional prefix range.
    """
    jobs: list[tuple[Path, str]] = []
    for phase in phases:
        phase_dir = PHASES_ROOT / phase
        if not phase_dir.exists():
            continue
        for src in sorted(phase_dir.glob("*.md")):
            if not is_source(src):
                continue

            stem_lc = src.stem.lower()

            # Letter filter
            if letter and not stem_lc.startswith(letter.lower()):
                continue

            # Prefix range filter: --prefix sa-sl
            if prefix:
                lo, _, hi = prefix.partition("-")
                if not lo or not hi:
                    sys.exit(f"--prefix must be lo-hi, e.g. sa-sl (got: {prefix!r})")
                lo_len = len(lo)
                stem_pfx = stem_lc[:lo_len]
                if not (lo.lower() <= stem_pfx <= hi.lower()):
                    continue

            # Skip if target already exists
            if out_path(src, lang).exists():
                continue

            jobs.append((src, src.read_text(encoding="utf-8").rstrip()))
    return jobs


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_report(phases: list[str]) -> None:
    total_done: dict[str, int] = {lang: 0 for lang in ALL_LANGS}
    total_src = 0

    for phase in phases:
        phase_dir = PHASES_ROOT / phase
        if not phase_dir.exists():
            continue
        src_files = [f for f in sorted(phase_dir.glob("*.md")) if is_source(f)]
        n = len(src_files)
        total_src += n
        print(f"\n{phase}  ({n} source files)")
        for lang in ALL_LANGS:
            done = sum(1 for f in src_files if out_path(f, lang).exists())
            total_done[lang] += done
            pct = 100 * done // n if n else 0
            bar = "█" * (done * 20 // n) + "░" * (20 - done * 20 // n) if n else ""
            print(f"  {lang}  {done:4d}/{n}  {pct:3d}%  {bar}")

    if len(phases) > 1:
        print(f"\nTotal source files: {total_src}")
        for lang in ALL_LANGS:
            d = total_done[lang]
            pct = 100 * d // total_src if total_src else 0
            print(f"  {lang}  {d:5d}/{total_src}  {pct}%")


def cmd_gen(
    phases: list[str],
    letter: str | None,
    prefix: str | None,
    langs: list[str],
    batch_size: int,
    workers: int,
    dry_run: bool,
) -> None:
    if dry_run:
        print("DRY RUN — no files will be written\n")

    client = None if dry_run else get_client()

    for lang in langs:
        jobs = collect_sources(phases, letter, prefix, lang)
        if not jobs:
            print(f"[{lang}] Nothing to do — all files already localized.")
            continue

        batches = [
            jobs[i: i + batch_size] for i in range(0, len(jobs), batch_size)
        ]
        print(
            f"[{lang}] {len(jobs)} files  "
            f"batch={batch_size}  batches={len(batches)}  workers={workers}",
            flush=True,
        )

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


# ── Entry point ───────────────────────────────────────────────────────────────

def parse_args() -> tuple[str, dict]:
    args = sys.argv[1:]
    cmd = args[0] if args else "report"

    opts: dict = {
        "phases": ALL_PHASES,
        "letter": None,
        "prefix": None,
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
        if a in ("--phase", "--phases"):
            v = nxt()
            opts["phases"] = ALL_PHASES if v == "all" else [f"phase_{v}"]
        elif a == "--letter":
            opts["letter"] = nxt()
        elif a == "--prefix":
            opts["prefix"] = nxt()
        elif a == "--lang":
            opts["langs"] = [x.strip().upper() for x in nxt().split(",")]
        elif a == "--batch":
            opts["batch"] = int(nxt())
        elif a == "--workers":
            opts["workers"] = int(nxt())
        elif a.startswith("--phase="):
            v = a.split("=", 1)[1]
            opts["phases"] = ALL_PHASES if v == "all" else [f"phase_{v}"]
        elif a.startswith("--letter="):
            opts["letter"] = a.split("=", 1)[1]
        elif a.startswith("--prefix="):
            opts["prefix"] = a.split("=", 1)[1]
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
        cmd_report(opts["phases"])
    elif cmd == "gen":
        cmd_gen(
            phases=opts["phases"],
            letter=opts["letter"],
            prefix=opts["prefix"],
            langs=opts["langs"],
            batch_size=opts["batch"],
            workers=opts["workers"],
            dry_run=opts["dry_run"],
        )
    else:
        sys.exit(f"Unknown command: {cmd!r}  (use 'gen' or 'report')")


if __name__ == "__main__":
    main()
