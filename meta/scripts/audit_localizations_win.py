#!/usr/bin/env python3
"""
audit_localizations_win.py — Windows variant of audit_localizations.py.

Changes vs the original (Linux) script:
  - sys.stdout.reconfigure(utf-8, errors=replace) for Windows console encoding
  - Path keys use .as_posix() so JSONL records always use forward slashes,
    compatible with Linux-generated logs on cross-platform re-runs
  - already_audited() normalises keys to forward slashes to match Linux logs

Usage on Windows (always use python3 -B to skip stale .pyc):
  python3 -B meta/scripts/audit_localizations_win.py run --corpus phases --lang JP --model google/gemma-4-26b-a4b-it --workers 4
  python3 -B meta/scripts/audit_localizations_win.py run --corpus phases --lang ZH --model google/gemma-4-26b-a4b-it --workers 4
  python3 -B meta/scripts/audit_localizations_win.py report

  # With log redirect:
  python3 -B meta/scripts/audit_localizations_win.py run --corpus phases --lang JP --model google/gemma-4-26b-a4b-it --workers 4 >> tmp/audit_phases_JP_openrouter.log 2>&1
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading

# Ensure stdout can handle non-ASCII on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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
            # Use assignment (not setdefault) so .env overrides inherited shell env vars.
            # Important on Windows where the shell env var may hold a revoked key.
            os.environ[_k.strip()] = _v.strip()

PHASES_ROOT = ROOT / "training_data" / "phases"
TMP = ROOT / "tmp"
OPENROUTER_MODEL = "deepseek/deepseek-v4-flash"
LOCAL_ENDPOINT = "http://192.168.3.5:1234/v1"
LOCAL_MODEL = "gemma-4-26b-a4b-it"
ALL_LANGS = ["JP", "ZH"]
ALL_PHASES = [f"phase_{i}" for i in range(1, 7)]

AUDIT_PROMPT = {
    "JP": """\
You are a Japanese localization quality auditor. You will review a Japanese training file
produced from an English source. Your job is to identify expressions that are unnatural,
word-for-word calques, or semantically wrong in the Japanese version.

SEVERITY LEVELS:
- CRITICAL: meaning is wrong or a native speaker would find it genuinely odd/incorrect
  Examples: inanimate object using a human action verb (座る for an acorn),
            calque phrase like 丸い上部を持つ instead of 上部が丸い,
            wrong register (着地する is for aircraft/parachutes, not falling objects)
- MINOR: slightly awkward but meaning is clear; optional fix

Report ONLY issues that are CRITICAL. Skip files that are acceptable.
If there are no critical issues, output exactly: OK

For issues, output a JSON object (no markdown, no code fences):
{
  "issues": [
    {"line": "the exact problematic Japanese line", "problem": "brief description", "suggestion": "better Japanese"}
  ]
}
""",
    "ZH": """\
You are a Traditional Chinese localization quality auditor. You will review a Traditional Chinese
training file produced from an English source. Your job is to identify expressions that are
unnatural, word-for-word calques, or semantically wrong in the Chinese version.

IMPORTANT: Only Traditional Chinese characters are acceptable. Flag any Simplified characters.

SEVERITY LEVELS:
- CRITICAL: meaning is wrong or a native speaker would find it genuinely odd/incorrect
  Examples: inanimate object using a human action verb (坐 for an acorn),
            calque phrase like 著陸 (for aircraft) used for a falling object,
            Simplified characters mixed in
- MINOR: slightly awkward but meaning is clear; optional fix

Report ONLY issues that are CRITICAL. Skip files that are acceptable.
If there are no critical issues, output exactly: OK

For issues, output a JSON object (no markdown, no code fences):
{
  "issues": [
    {"line": "the exact problematic Chinese line", "problem": "brief description", "suggestion": "better Traditional Chinese"}
  ]
}
""",
}


def get_client(endpoint: str | None = None) -> OpenAI:
    if endpoint:
        return OpenAI(base_url=endpoint, api_key="local")
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


def is_source(path: Path, src_suffix: str) -> bool:
    """True if this is a source file (not a lang sibling)."""
    if src_suffix:
        return path.stem.endswith(f"_{src_suffix}")
    return not path.stem.endswith(("_DE", "_JP", "_ZH", "_EN"))


def loc_path(src: Path, lang: str, src_suffix: str) -> Path:
    if src_suffix:
        # e.g. category_01_EN.md → category_01_JP.md
        stem_base = src.stem[: -len(src_suffix) - 1]  # strip _EN
        return src.parent / f"{stem_base}_{lang}.md"
    return src.parent / f"{src.stem}_{lang}.md"


def collect_pairs(
    src_dirs: list[Path],
    lang: str,
    src_suffix: str,
) -> list[tuple[Path, Path]]:
    pairs = []
    for d in src_dirs:
        if not d.exists():
            continue
        for src in sorted(d.glob("*.md")):
            if not is_source(src, src_suffix):
                continue
            loc = loc_path(src, lang, src_suffix)
            if loc.exists():
                pairs.append((src, loc))
    return pairs


def audit_file(src: Path, loc: Path, lang: str, client: OpenAI, model: str) -> dict | None:
    """Return a result dict or None if OK."""
    en_text = src.read_text(encoding="utf-8").strip()
    loc_text = loc.read_text(encoding="utf-8").strip()

    system_prompt = AUDIT_PROMPT[lang]
    user_msg = (
        f"English source:\n{en_text}\n\n"
        f"{lang} localization:\n{loc_text}"
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            max_tokens=1024,
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        return {"file": str(loc), "error": str(exc)}

    if raw.upper() == "OK" or raw.strip() == "":
        return None

    try:
        data = json.loads(raw)
        issues = data.get("issues", [])
        if not issues:
            return None
        return {
            "file": str(loc),
            "src": str(src),
            "issues": issues,
        }
    except json.JSONDecodeError:
        if "OK" in raw[:10]:
            return None
        return {
            "file": str(loc),
            "src": str(src),
            "raw_response": raw[:500],
        }


def audit_log_path(lang: str, label: str = "phases") -> Path:
    return TMP / f"audit_{lang}_{label}.jsonl"


def already_audited(log_path: Path) -> set[str]:
    done = set()
    if not log_path.exists():
        return done
    for line in log_path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
            # Normalize to forward slashes so Linux-written logs match Windows paths
            k = rec.get("file", "").replace("\\", "/")
            done.add(k)
        except Exception:
            pass
    return done


def cmd_run(
    src_dirs: list[Path],
    label: str,
    lang: str,
    workers: int,
    endpoint: str | None,
    model: str,
    src_suffix: str,
) -> None:
    client = get_client(endpoint)
    pairs = collect_pairs(src_dirs, lang, src_suffix)
    log_path = audit_log_path(lang, label)
    done = already_audited(log_path)

    # Use POSIX relative path for dedup key (forward slashes on all platforms)
    pending = [
        (src, loc) for src, loc in pairs
        if loc.relative_to(ROOT).as_posix() not in done
    ]

    if not pending:
        print(f"[{lang}/{label}] Nothing new to audit ({len(pairs)} files already audited).")
        return

    source = endpoint or "openrouter"
    print(f"[{lang}/{label}] Auditing {len(pending)} files via {source} / {model} "
          f"(skipping {len(pairs) - len(pending)} already done)")

    lock = threading.Lock()
    flagged = ok = errors = 0

    def process(src: Path, loc: Path) -> None:
        nonlocal flagged, ok, errors
        rel = loc.relative_to(ROOT).as_posix()
        try:
            result = audit_file(src, loc, lang, client, model)
        except Exception as exc:
            with lock:
                errors += 1
                print(f"  ERROR {rel}: {exc}", flush=True)
            return
        with lock:
            if result is None:
                ok += 1
                print(f"  OK   {rel}", flush=True)
            elif "error" in result:
                errors += 1
                print(f"  ERROR {rel}: {result['error']}", flush=True)
                log_path.parent.mkdir(exist_ok=True)
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"file": rel, "error": result["error"]}) + "\n")
            else:
                flagged += 1
                n = len(result.get("issues", []))
                print(f"  FLAG  {rel} ({n} issues)", flush=True)
                log_path.parent.mkdir(exist_ok=True)
                result["file"] = rel
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(result) + "\n")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(as_completed([pool.submit(process, s, l) for s, l in pending]))

    print(f"\n[{lang}/{label}] done: {ok} OK, {flagged} flagged, {errors} errors.")
    print(f"Audit log: {log_path}")


def cmd_report(langs: list[str]) -> None:
    logs = sorted(TMP.glob("audit_*.jsonl")) if TMP.exists() else []
    if not logs:
        print("No audit logs found in tmp/")
        return
    for log_path in logs:
        records = []
        for line in log_path.read_text(encoding="utf-8").splitlines():
            try:
                records.append(json.loads(line))
            except Exception:
                pass
        # deduplicate by file key
        seen: set[str] = set()
        uniq = []
        for r in records:
            k = r.get("file", "")
            if k not in seen:
                seen.add(k)
                uniq.append(r)
        flagged = [r for r in uniq if "issues" in r]
        errors = [r for r in uniq if "error" in r]
        print(f"\n{log_path.name}: {len(uniq)} audited — {len(flagged)} flagged, {len(errors)} errors")
        for r in flagged[:5]:
            issues = r.get("issues", [])
            print(f"  {r['file']}: {len(issues)} issue(s)")
            for iss in issues[:1]:
                print(f"    • {iss.get('problem', '')} → {iss.get('suggestion', '')}")
        if len(flagged) > 5:
            print(f"  ... and {len(flagged) - 5} more")


TRIPLETS_ROOT = ROOT / "training_data" / "triplet_stories"

# (base, subdirs, src_suffix, log_label)
KNOWN_DIRS = {
    "phases":          (PHASES_ROOT,    [f"phase_{i}" for i in range(1, 7)], "",   "phases"),
    "reasoning":       (ROOT / "training_data" / "reasoning", ["."],          "",   "reasoning"),
    "triplets":        (TRIPLETS_ROOT,  ["tier_1","tier_2","tier_3","tier_4"],"EN", "triplets"),
    "triplets_1":      (TRIPLETS_ROOT,  ["tier_1"],                           "EN", "triplets"),
    "triplets_2":      (TRIPLETS_ROOT,  ["tier_2"],                           "EN", "triplets"),
    "triplets_3":      (TRIPLETS_ROOT,  ["tier_3"],                           "EN", "triplets"),
    "triplets_4":      (TRIPLETS_ROOT,  ["tier_4"],                           "EN", "triplets"),
    "grounded":        (ROOT / "training_data" / "grounded_stories", ["."],   "EN", "grounded"),
}


def resolve_src_dirs(corpus: str) -> tuple[list[Path], str, str]:
    """Return (list_of_dirs, label, src_suffix) for a named corpus."""
    if corpus not in KNOWN_DIRS:
        sys.exit(f"Unknown corpus {corpus!r}. Choose from: {', '.join(KNOWN_DIRS)}")
    base, subdirs, suffix, label = KNOWN_DIRS[corpus]
    dirs = [base / s if s != "." else base for s in subdirs]
    return dirs, label, suffix


def parse_args() -> tuple[str, dict]:
    args = sys.argv[1:]
    cmd = args[0] if args else "report"

    opts: dict = {
        "corpus": "phases",
        "phase_filter": None,
        "langs": ALL_LANGS[:],
        "workers": 2,
        "endpoint": None,
        "model": OPENROUTER_MODEL,
    }

    i = 1
    while i < len(args):
        a = args[i]
        def nxt() -> str:
            nonlocal i; i += 1; return args[i]
        if a in ("--phase", "--phases"):
            opts["phase_filter"] = nxt()
        elif a == "--corpus":
            opts["corpus"] = nxt()
        elif a == "--lang":
            opts["langs"] = [x.strip().upper() for x in nxt().split(",")]
        elif a == "--workers":
            opts["workers"] = int(nxt())
        elif a == "--endpoint":
            opts["endpoint"] = nxt()
        elif a == "--model":
            opts["model"] = nxt()
        elif a == "--local":
            opts["endpoint"] = LOCAL_ENDPOINT
            opts["model"] = LOCAL_MODEL
            if opts["workers"] > 2:
                opts["workers"] = 2
        elif a.startswith("--phase="):
            opts["phase_filter"] = a.split("=", 1)[1]
        elif a.startswith("--corpus="):
            opts["corpus"] = a.split("=", 1)[1]
        elif a.startswith("--lang="):
            opts["langs"] = [x.strip().upper() for x in a.split("=", 1)[1].split(",")]
        elif a.startswith("--workers="):
            opts["workers"] = int(a.split("=", 1)[1])
        elif a.startswith("--endpoint="):
            opts["endpoint"] = a.split("=", 1)[1]
        elif a.startswith("--model="):
            opts["model"] = a.split("=", 1)[1]
        i += 1

    return cmd, opts


def main() -> None:
    cmd, opts = parse_args()

    if cmd == "report":
        cmd_report(opts["langs"])
    elif cmd == "run":
        src_dirs, label, src_suffix = resolve_src_dirs(opts["corpus"])

        # Phase filter (phases corpus only)
        if opts["phase_filter"] and opts["corpus"] == "phases":
            pf = opts["phase_filter"]
            if pf != "all":
                src_dirs = [PHASES_ROOT / f"phase_{pf}"]
            label = f"phases_p{pf}" if pf != "all" else "phases"

        for lang in opts["langs"]:
            cmd_run(
                src_dirs=src_dirs,
                label=label,
                lang=lang,
                workers=opts["workers"],
                endpoint=opts["endpoint"],
                model=opts["model"],
                src_suffix=src_suffix,
            )
    else:
        sys.exit(f"Unknown command: {cmd!r}  (use 'run' or 'report')")


if __name__ == "__main__":
    main()
