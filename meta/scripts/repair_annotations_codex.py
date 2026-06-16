#!/usr/bin/env python3
"""
repair_annotations_codex.py — Repair _marked.md annotation errors using codex exec.

Sends 4 codex exec calls per file (one per language: EN, DE, JP, ZH).
Codex reads and edits the file directly — no content in prompt.
Backs up the file before editing; restores on verify failure.

Sources:
  --failed-only   parse tmp/repair_annotations_full_run.log for FAIL entries (default)
  --all           all _marked.md files not already in done file
  --files f ...   explicit list

Usage:
  python3 meta/scripts/repair_annotations_codex.py
  python3 meta/scripts/repair_annotations_codex.py --failed-only --workers 4
  python3 meta/scripts/repair_annotations_codex.py --all --workers 4
  python3 meta/scripts/repair_annotations_codex.py --files training_data/.../foo_marked.md
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT        = Path(__file__).resolve().parent.parent.parent
STORIES_DIR = ROOT / "training_data" / "01_language" / "teaching_stories"
FAIL_LOG    = ROOT / "tmp" / "repair_annotations_full_run.log"

CODEX_BIN   = "codex"   # must be on PATH; verified present at ~/.nvm/.../bin/codex

# Reasoning effort: "low" | "medium" | "high" — override with --effort
DEFAULT_EFFORT = "medium"

_print_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Per-language prompts — codex edits the file in place
# ---------------------------------------------------------------------------

LANG_CALLS = [
    ("EN", "English",  "the FIRST  [user]/[Ninereeds] pair"),
    ("DE", "German",   "the SECOND [user]/[Ninereeds] pair"),
    ("JP", "Japanese", "the THIRD  [user]/[Ninereeds] pair"),
    ("ZH", "Chinese",  "the FOURTH [user]/[Ninereeds] pair"),
]

PROMPT_TEMPLATE = """\
Fix the {language} [Ninereeds] annotation block in the file:
  {path}

Edit ONLY {pair} — the [Ninereeds] block that follows the {language} [user] line.
Leave every other section (other [Ninereeds] blocks and all [user] lines) exactly as-is.

ANNOTATION RULES (apply only to the [Ninereeds] block you are fixing):
1. Every sentence must have (NOM) and *verb*.
   (NOM) = full subject NP including articles/determiners.
   *verb* = single main content verb ONLY — no auxiliaries, modals, negation, or participles.
2. [user] lines must be left completely untouched.
3. {ACC} wraps the full direct-object NP.
4. [DAT] wraps the full dative NP or locative PP including the preposition.
5. <GEN> wraps the genitive/possessive modifier only, sits directly before the noun it modifies.
6. Do NOT add brackets ({ACC}, [DAT], <GEN>) where the role is not present in the sentence.
7. Adverbs and time expressions are NOT subjects — do not wrap them in (NOM).
   Remove: (Later,)  (Dann)  (Später)  (今日は)  (然後)  etc.
8. Negation stays OUTSIDE *verb*:
   Good: (Er) *gab* nicht auf
   Bad:  (Er) *gab nicht auf*
9. For JP/ZH topic-drop: identify the implied subject and add it inside (NOM).
10. 把-constructions in ZH: bracket as (subject) *verb* {{把 + NP}}.
11. Empty () brackets are errors — always put the subject inside.
12. Do NOT paraphrase, reword, or change any source text. Only change annotation brackets.
13. Do NOT add or remove [user]/[Ninereeds] tags.

Save the file when done.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def done_file_for(effort: str) -> Path:
    """Done file is effort-specific so medium and high passes don't collide."""
    return ROOT / "tmp" / f"repair_codex_{effort}_done.txt"


def load_done(effort: str) -> set[str]:
    df = done_file_for(effort)
    if df.exists():
        return set(df.read_text("utf-8").splitlines())
    return set()


def mark_done(slug: str, effort: str) -> None:
    with open(done_file_for(effort), "a", encoding="utf-8") as f:
        f.write(slug + "\n")


def path_to_slug(p: Path) -> str:
    return str(p.relative_to(STORIES_DIR))


def verify_output(original: str, repaired: str) -> str | None:
    orig_tags   = re.findall(r"\[user\]|\[Ninereeds\]", original)
    repair_tags = re.findall(r"\[user\]|\[Ninereeds\]", repaired)
    if orig_tags != repair_tags:
        return f"tag mismatch: expected {len(orig_tags)}, got {len(repair_tags)}"
    if "(" not in repaired or "*" not in repaired:
        return "annotation brackets missing"
    if len(repaired) < len(original) * 0.75:
        return f"output too short ({len(repaired)} vs {len(original)})"
    return None


def files_from_fail_log(log_path: Path) -> list[Path]:
    """Parse repair_annotations_full_run.log and return paths of all FAIL entries."""
    if not log_path.exists():
        sys.exit(f"ERROR: fail log not found: {log_path}")
    paths: list[Path] = []
    seen: set[str] = set()
    for line in log_path.read_text("utf-8", errors="replace").splitlines():
        if "FAIL" not in line:
            continue
        # Line format: "  [NNN/5006] FAIL    tier_X/category/file_marked.md: reason"
        m = re.search(r"FAIL\s+(tier_\S+_marked\.md)", line)
        if not m:
            continue
        rel = m.group(1).split(":")[0].strip()
        if rel in seen:
            continue
        seen.add(rel)
        p = STORIES_DIR / rel
        if p.exists():
            paths.append(p)
        else:
            print(f"  WARN: not found: {rel}", file=sys.stderr)
    return paths


# ---------------------------------------------------------------------------
# Core repair
# ---------------------------------------------------------------------------

def run_codex(prompt: str, cwd: Path, effort: str, timeout: int = 240) -> tuple[bool, str]:
    """Run a single codex exec call. Returns (success, stderr_or_error)."""
    try:
        result = subprocess.run(
            [CODEX_BIN, "exec",
             "-c", f"model_reasoning_effort={effort}",
             prompt],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return False, (result.stderr or result.stdout or "non-zero exit").strip()
        return True, ""
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s"
    except Exception as e:
        return False, str(e)


def repair_file(path: Path, effort: str) -> tuple[Path, bool, str]:
    original = path.read_text("utf-8")

    # Back up before any edits
    _, backup_path_str = tempfile.mkstemp(suffix=".bak")
    backup_path = Path(backup_path_str)
    try:
        backup_path.write_text(original, "utf-8")

        for lang_code, language, pair in LANG_CALLS:
            prompt = (PROMPT_TEMPLATE
                      .replace("{language}", language)
                      .replace("{path}", str(path))
                      .replace("{pair}", pair))
            ok, err = run_codex(prompt, cwd=ROOT, effort=effort)
            if not ok:
                shutil.copy(backup_path, path)
                return path, False, f"{lang_code} codex error: {err}"

        repaired = path.read_text("utf-8")
        err = verify_output(original, repaired)
        if err:
            shutil.copy(backup_path, path)
            return path, False, f"verify: {err}"

        return path, True, "ok"

    finally:
        backup_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def cmd_run(args) -> None:
    effort   = args.effort
    codex_log = ROOT / "tmp" / f"repair_codex_{effort}_run.log"

    # Build file list
    if args.files:
        targets = [Path(f) if Path(f).is_absolute() else ROOT / f for f in args.files]
    elif args.all:
        targets = sorted(STORIES_DIR.rglob("*_marked.md"))
    else:
        # Default: files that failed the DeepSeek pass
        targets = files_from_fail_log(FAIL_LOG)
        if not targets:
            print("No failed files found in log. Use --all to process everything.")
            return

    done_slugs = load_done(effort)
    pending    = [p for p in targets if path_to_slug(p) not in done_slugs]
    skipped    = len(targets) - len(pending)

    print(f"Effort: {effort} | {len(targets)} files total | {skipped} already done | {len(pending)} to repair")
    if not pending:
        print("Nothing to do.")
        return

    ok = fail = 0
    log_handle = open(codex_log, "a", encoding="utf-8")

    def log(msg: str) -> None:
        print(msg)
        log_handle.write(msg + "\n")
        log_handle.flush()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(repair_file, p, effort): p for p in pending}
        done_count = skipped
        for fut in as_completed(futures):
            path, success, msg = fut.result()
            done_count += 1
            slug = path_to_slug(path)
            rel  = path.relative_to(STORIES_DIR)
            with _print_lock:
                if success:
                    line = f"  [{done_count:4d}/{len(targets)}] OK      {rel}"
                    ok += 1
                else:
                    line = f"  [{done_count:4d}/{len(targets)}] FAIL    {rel}: {msg}"
                    fail += 1
                log(line)
            if success:
                mark_done(slug, effort)

    summary = f"\nDone: {ok} repaired, {skipped} skipped, {fail} failed"
    log(summary)
    log_handle.close()

    if fail:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repair _marked.md annotation errors via codex exec (gpt-5.4-mini)."
    )
    parser.add_argument("--failed-only", action="store_true",
                        help="Only process files that failed the DeepSeek pass (default)")
    parser.add_argument("--all", action="store_true",
                        help="Process all _marked.md files")
    parser.add_argument("--files", nargs="+",
                        help="Explicit list of _marked.md paths")
    parser.add_argument("--workers", type=int, default=4,
                        help="Parallel codex processes (default: 4)")
    parser.add_argument("--effort", choices=["low", "medium", "high"], default=DEFAULT_EFFORT,
                        help=f"Reasoning effort for codex (default: {DEFAULT_EFFORT})")
    args = parser.parse_args()
    cmd_run(args)


if __name__ == "__main__":
    main()
