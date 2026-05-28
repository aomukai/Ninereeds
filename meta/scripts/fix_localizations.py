#!/usr/bin/env python3
"""
fix_localizations.py — Apply fixes from audit log to flagged JP/ZH phase files.

Reads the audit JSONL produced by audit_localizations.py, then for each flagged file
sends DeepSeek the EN source, the flawed localization, and the audit issues, and asks
it to produce a corrected version.

Writes corrected files in place. Records completed fixes in tmp/fix_<lang>_done.txt.

Usage:
  python3 meta/scripts/fix_localizations.py run --lang JP [--workers 4]
  python3 meta/scripts/fix_localizations.py run --lang ZH --workers 6
  python3 meta/scripts/fix_localizations.py report --lang JP
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

PHASES_ROOT = ROOT / "training_data" / "phases"
TMP = ROOT / "tmp"
MODEL = "deepseek/deepseek-v4-flash"
ALL_LANGS = ["JP", "ZH"]

FIX_PROMPT = {
    "JP": """\
You are fixing a Japanese localization of a training file. The file has specific issues
identified by an auditor. Your job is to produce a corrected Japanese version that:
1. Fixes every issue listed
2. Keeps all correct lines UNCHANGED
3. Preserves the exact [user]/[Ninereeds] structure and line count of the original
4. Uses natural Japanese — no word-for-word calques, appropriate verbs for the subject

Rules:
- Plain form (だ/である). No ですます.
- Do NOT use pronouns (それ、その、彼、彼女 etc.) — repeat the noun.
- Match the source line count exactly.
- Output ONLY the corrected file content — no preamble, no explanation.
""",
    "ZH": """\
You are fixing a Traditional Chinese localization of a training file. The file has specific
issues identified by an auditor. Your job is to produce a corrected Traditional Chinese
version that:
1. Fixes every issue listed
2. Keeps all correct lines UNCHANGED
3. Preserves the exact [user]/[Ninereeds] structure and line count of the original
4. Uses natural Traditional Chinese — no word-for-word calques, appropriate verbs for the subject
5. TRADITIONAL characters ONLY throughout

Rules:
- Do NOT use pronouns (它、牠、他、她、其 etc.) — repeat the noun.
- Match the source line count exactly.
- Output ONLY the corrected file content — no preamble, no explanation.
""",
}


def get_client() -> OpenAI:
    key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
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


def count_tag(text: str, tag: str) -> int:
    return len(re.findall(rf"^\[{re.escape(tag)}\]", text, re.MULTILINE))


def _block_line_counts(text: str) -> list[int]:
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
        elif in_block and line.strip():
            current += 1
    if in_block:
        counts.append(current)
    return counts


def validate(source: str, output: str, lang: str) -> list[str]:
    errs = []
    if count_tag(output, "user") != count_tag(source, "user"):
        errs.append("[user] count mismatch")
    if count_tag(output, "Ninereeds") != count_tag(source, "Ninereeds"):
        errs.append("[Ninereeds] count mismatch")
    src_c = _block_line_counts(source)
    out_c = _block_line_counts(output)
    if src_c != out_c:
        errs.append(f"line counts {out_c} ≠ source {src_c}")
    if lang == "ZH":
        simplified_sample = "给苹玛铅篮邻个来说为国"
        if any(ch in output for ch in simplified_sample):
            errs.append("Simplified Chinese found")
    if lang == "JP" and not re.search(r"[぀-ヿ]", output):
        errs.append("No Japanese characters")
    return errs


def fix_file(record: dict, lang: str, client: OpenAI) -> str:
    src_rel = record.get("src", "")
    loc_rel = record.get("file", "")
    src_path = PHASES_ROOT / src_rel
    loc_path = PHASES_ROOT / loc_rel

    if not src_path.exists():
        return f"  MISSING_SRC {src_rel}"
    if not loc_path.exists():
        return f"  MISSING_LOC {loc_rel}"

    en_text = src_path.read_text(encoding="utf-8").strip()
    loc_text = loc_path.read_text(encoding="utf-8").strip()
    issues = record.get("issues", [])
    issues_text = "\n".join(
        f"- Line: {iss.get('line', '?')}\n  Problem: {iss.get('problem', '?')}\n  Suggestion: {iss.get('suggestion', '')}"
        for iss in issues
    )

    user_msg = (
        f"English source:\n{en_text}\n\n"
        f"Current {lang} (has issues):\n{loc_text}\n\n"
        f"Issues to fix:\n{issues_text}"
    )

    for attempt in range(1, 3):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                max_tokens=8192,
                messages=[
                    {"role": "system", "content": FIX_PROMPT[lang]},
                    {"role": "user", "content": user_msg},
                ],
            )
            raw = (resp.choices[0].message.content or "").strip()
        except Exception as exc:
            return f"  ERROR {loc_rel}: {exc}"

        errs = validate(en_text, raw, lang)
        if errs:
            if attempt == 1:
                continue
            return f"  FAIL {loc_rel}: {'; '.join(errs)}"

        loc_path.write_text(raw + "\n", encoding="utf-8")
        return f"  FIXED {loc_rel}"

    return f"  FAIL {loc_rel}: all attempts failed"


def done_path(lang: str) -> Path:
    return TMP / f"fix_{lang}_done.txt"


def already_fixed(lang: str) -> set[str]:
    p = done_path(lang)
    if not p.exists():
        return set()
    return set(p.read_text(encoding="utf-8").splitlines())


def cmd_run(lang: str, workers: int) -> None:
    audit_log = TMP / f"audit_{lang}.jsonl"
    if not audit_log.exists():
        sys.exit(f"No audit log found at {audit_log}. Run audit_localizations.py first.")

    records = []
    for line in audit_log.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
            if "issues" in r and r["issues"]:
                records.append(r)
        except Exception:
            pass

    done = already_fixed(lang)
    pending = [r for r in records if r.get("file", "") not in done]

    if not pending:
        print(f"[{lang}] Nothing to fix ({len(records)} records in log, all done).")
        return

    print(f"[{lang}] Fixing {len(pending)} flagged files (skipping {len(records) - len(pending)} already fixed)")

    client = get_client()
    lock = threading.Lock()
    fixed = fail = 0

    def process(record: dict) -> None:
        nonlocal fixed, fail
        result = fix_file(record, lang, client)
        with lock:
            print(result, flush=True)
            if "FIXED" in result:
                fixed += 1
                with done_path(lang).open("a", encoding="utf-8") as f:
                    f.write(record.get("file", "") + "\n")
            else:
                fail += 1

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(as_completed([pool.submit(process, r) for r in pending]))

    print(f"\n[{lang}] done: {fixed} fixed, {fail} failed.")


def cmd_report(langs: list[str]) -> None:
    for lang in langs:
        audit_log = TMP / f"audit_{lang}.jsonl"
        done = already_fixed(lang)
        if not audit_log.exists():
            print(f"[{lang}] No audit log.")
            continue
        records = [json.loads(l) for l in audit_log.read_text().splitlines() if l.strip()]
        flagged = [r for r in records if "issues" in r]
        remaining = [r for r in flagged if r.get("file", "") not in done]
        print(f"[{lang}] {len(flagged)} flagged, {len(done)} fixed, {len(remaining)} remaining")


def parse_args() -> tuple[str, dict]:
    args = sys.argv[1:]
    cmd = args[0] if args else "report"
    opts: dict = {"langs": ALL_LANGS[:], "workers": 4}

    i = 1
    while i < len(args):
        a = args[i]
        def nxt() -> str:
            nonlocal i; i += 1; return args[i]
        if a == "--lang":
            opts["langs"] = [x.strip().upper() for x in nxt().split(",")]
        elif a == "--workers":
            opts["workers"] = int(nxt())
        elif a.startswith("--lang="):
            opts["langs"] = [x.strip().upper() for x in a.split("=", 1)[1].split(",")]
        elif a.startswith("--workers="):
            opts["workers"] = int(a.split("=", 1)[1])
        i += 1

    return cmd, opts


def main() -> None:
    cmd, opts = parse_args()

    if cmd == "report":
        cmd_report(opts["langs"])
    elif cmd == "run":
        for lang in opts["langs"]:
            cmd_run(lang, opts["workers"])
    else:
        sys.exit(f"Unknown command: {cmd!r}  (use 'run' or 'report')")


if __name__ == "__main__":
    main()
