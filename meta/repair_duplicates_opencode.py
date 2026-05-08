#!/usr/bin/env python3
"""
Repair duplicate/redundant corpus files with opencode + DeepSeek v4 flash.

This runner is queue-driven and resumable:
- reads training_data/phases/repair_duplicate.txt
- skips files already listed in training_data/phases/repair_progress_duplicate.txt
- rewrites one file at a time via opencode
- appends the file path to the progress ledger only after a verified write

Usage:
  python3 meta/repair_duplicates_opencode.py --dry-run
  python3 meta/repair_duplicates_opencode.py --batch 5
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import shutil
import subprocess
import sys
import threading
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
QUEUE_PATH = REPO_ROOT / "training_data/phases/repair_duplicate.txt"
PROGRESS_PATH = REPO_ROOT / "training_data/phases/repair_progress_duplicate.txt"
SKIPPED_PATH = REPO_ROOT / "training_data/phases/repair_skipped_duplicate.txt"
_opencode_which = shutil.which("opencode")
OPENCODE_BIN = Path(_opencode_which) if _opencode_which else (Path.home() / ".opencode/bin/opencode")
MODEL = "openrouter/deepseek/deepseek-v4-flash"
DEBUG_DIR = REPO_ROOT / "tmp/opencode_duplicate_debug"
PROGRESS_LOCK = threading.Lock()
PRINT_LOCK = threading.Lock()

FORMAT_SPEC = """\
Keep the existing file template unless the current structure is clearly broken.

Format A:
- Preserve the same block count already present in the file
- Keep each [Ninereeds] opener on one line
- Preserve blank-line separation between blocks
- Remove duplicate or redundant lines
- Replace removed lines with concrete valid lines
- No pronouns
- No negation
- Keep each sentence anchored to the target subject
- Each content line must be exactly one sentence
- Summary lines must combine two concrete true properties from the block
- Do not invent abstract labels like "passage", "presence", "thing", or "object" when a concrete description is available

Phase 5 one-block action files:
- Keep the single block
- Keep 6 body lines after the opener
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair duplicate queue via opencode")
    parser.add_argument("--batch", type=int, default=10, help="Number of files to process")
    parser.add_argument("--workers", type=int, default=10, help="Parallel opencode workers")
    parser.add_argument("--dry-run", action="store_true", help="List pending files without editing")
    parser.add_argument("--timeout", type=int, default=180, help="Per-file timeout in seconds")
    return parser.parse_args()


def read_progress() -> list[str]:
    if not PROGRESS_PATH.exists():
        return []
    return [line.strip() for line in PROGRESS_PATH.read_text().splitlines() if line.strip()]


def append_progress(path_str: str) -> None:
    with PROGRESS_LOCK:
        with PROGRESS_PATH.open("a", encoding="utf-8") as fh:
            fh.write(path_str + "\n")


def append_skipped(path_str: str, reason: str) -> None:
    with PROGRESS_LOCK:
        existing = set()
        if SKIPPED_PATH.exists():
            existing = {
                line.split("|", 1)[0].strip()
                for line in SKIPPED_PATH.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
        if path_str in existing:
            return
        with SKIPPED_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"{path_str} | {reason}\n")


def log(msg: str) -> None:
    with PRINT_LOCK:
        print(msg, flush=True)


def parse_queue() -> list[dict]:
    entries_by_path: OrderedDict[str, dict] = OrderedDict()
    for raw_line in QUEUE_PATH.read_text().splitlines():
        line = raw_line.strip()
        if not line or ".md" not in line or "|" not in line:
            continue
        parts = [part.strip() for part in line.split("|", 2)]
        if len(parts) != 3:
            continue
        path_str, issue_type, reason = parts
        if not path_str.endswith(".md"):
            continue
        entry = entries_by_path.setdefault(
            path_str,
            {"path": path_str, "issue_types": [], "reasons": []},
        )
        entry["issue_types"].append(issue_type)
        entry["reasons"].append(reason)
    return list(entries_by_path.values())


def partition_existing(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    existing = []
    missing = []
    for entry in entries:
        path = REPO_ROOT / entry["path"]
        if path.exists():
            existing.append(entry)
        else:
            missing.append(entry)
    return existing, missing


def read_file(path_str: str) -> str:
    path = REPO_ROOT / path_str
    return path.read_text(encoding="utf-8")


def find_counterparts(reason_text: str, current_path: str) -> list[str]:
    matches = re.findall(r"(phase_\d+_\d+\.md|adj_rewrites\.md)", reason_text)
    counterparts: list[str] = []
    for match in matches:
        if match == Path(current_path).name:
            continue
        if match == "adj_rewrites.md":
            resolved = "training_data/phases/adj_rewrites.md"
        else:
            phase_match = re.match(r"^(phase_\d+)_", match)
            if not phase_match:
                continue
            resolved = f"training_data/phases/{phase_match.group(1)}/{match}"
        if resolved != current_path and resolved not in counterparts:
            counterparts.append(resolved)
    return counterparts


def build_prompt(entry: dict, retry: bool = False) -> str:
    path_str = entry["path"]
    current_content = read_file(path_str)
    reason_blob = "\n".join(f"- {reason}" for reason in entry["reasons"])
    counterpart_sections: list[str] = []
    seen_counterparts: list[str] = []
    for reason in entry["reasons"]:
        for counterpart in find_counterparts(reason, path_str):
            if counterpart in seen_counterparts:
                continue
            seen_counterparts.append(counterpart)
            try:
                counterpart_content = read_file(counterpart)
            except FileNotFoundError:
                counterpart_content = "[missing counterpart file]"
            counterpart_sections.append(
                f"Counterpart file: {counterpart}\n"
                f"--- BEGIN COUNTERPART ---\n{counterpart_content}\n--- END COUNTERPART ---"
            )
    counterpart_blob = "\n\n".join(counterpart_sections) if counterpart_sections else "None."

    retry_note = ""
    if retry:
        retry_note = (
            "Previous attempt returned a receipt or non-file output.\n"
            "This call is only generating replacement file text for one file.\n"
            "Do not return a receipt. Do not mention status. Output only the rewritten file.\n\n"
        )

    return f"""{retry_note}Rewrite the target file to remove duplicate, repeated, or redundant lines while preserving the target word and the correct curriculum format.

Hard rules:
- Output ONLY the full corrected contents of the target file.
- Do not include commentary, markdown fences, notes, or explanations.
- Do not modify counterpart files.
- Keep the same file type and block count unless the reason clearly shows the current structure is invalid.
- If the issue is cross-file duplication, make this target file distinct and valid rather than copying counterpart phrasing.
- Think as long as needed, but the final answer must be only the rewritten file text.

{FORMAT_SPEC}

Target file: {path_str}
Issue types: {", ".join(entry["issue_types"])}
Reasons:
{reason_blob}

Counterpart context:
{counterpart_blob}

Current target file contents:
--- BEGIN TARGET ---
{current_content}
--- END TARGET ---
"""


def run_opencode(prompt: str, timeout: int) -> tuple[str, str]:
    cmd = [
        str(OPENCODE_BIN),
        "run",
        "--format",
        "json",
        "-m",
        MODEL,
        "--dangerously-skip-permissions",
        prompt,
    ]
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"opencode exited {proc.returncode}")

    text_parts: list[str] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "text":
            text = event.get("part", {}).get("text", "")
            if text:
                text_parts.append(text)
    response = "".join(text_parts).strip()
    if not response:
        raise RuntimeError("opencode returned no text content")
    return response, proc.stdout


def normalize_response(text: str) -> str:
    cleaned = text.strip()
    if "[user]" in cleaned:
        cleaned = cleaned[cleaned.index("[user]") :]
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()
    return cleaned + "\n"


def looks_like_receipt(text: str) -> bool:
    stripped = text.lstrip()
    if stripped.startswith("RECEIPT"):
        return True
    if "Status:" in stripped and "Files processed this run:" in stripped:
        return True
    return False


def verify_rewrite(path_str: str, content: str) -> None:
    if "[user]" not in content or "[Ninereeds]" not in content:
        raise RuntimeError(f"{path_str}: missing required tags after rewrite")
    if len(content.strip()) < 40:
        raise RuntimeError(f"{path_str}: rewritten content is unexpectedly short")
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("[user]"):
            continue
        if stripped.startswith("[Ninereeds]"):
            if stripped.count(".") != 1:
                raise RuntimeError(f"{path_str}: opener line must contain exactly one sentence")
            continue
        if stripped.count(".") != 1:
            raise RuntimeError(f"{path_str}: content line must contain exactly one sentence")


def process_entry(entry: dict, timeout: int, dry_run: bool) -> tuple[bool, str]:
    path_str = entry["path"]
    if dry_run:
        log(f"[DRY RUN] {path_str}")
        for reason in entry["reasons"]:
            log(f"  - {reason}")
        return True, "dry-run"

    prompts = [build_prompt(entry, retry=False), build_prompt(entry, retry=True)]
    response = ""
    raw = ""
    new_content = ""
    last_error = None
    for prompt in prompts:
        response, raw = run_opencode(prompt, timeout=timeout)
        if looks_like_receipt(response):
            last_error = RuntimeError(f"{path_str}: model returned receipt text instead of file contents")
            continue
        new_content = normalize_response(response)
        try:
            verify_rewrite(path_str, new_content)
            last_error = None
            break
        except Exception as exc:
            last_error = exc
            continue
    if last_error is not None:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        debug_name = Path(path_str).name + ".response.txt"
        debug_text = new_content if new_content else response
        (DEBUG_DIR / debug_name).write_text(debug_text, encoding="utf-8")
        (DEBUG_DIR / (Path(path_str).name + ".events.jsonl")).write_text(raw, encoding="utf-8")
        raise last_error

    path = REPO_ROOT / path_str
    path.write_text(new_content, encoding="utf-8")
    confirmed = path.read_text(encoding="utf-8")
    verify_rewrite(path_str, confirmed)
    append_progress(path_str)
    log(f"OK {path_str}")
    return True, "ok"


def main() -> int:
    args = parse_args()
    if not OPENCODE_BIN.exists():
        print(f"ERROR: opencode binary not found at {OPENCODE_BIN}", file=sys.stderr)
        return 1
    if not QUEUE_PATH.exists():
        print(f"ERROR: queue not found at {QUEUE_PATH}", file=sys.stderr)
        return 1

    all_entries = parse_queue()
    all_entries, missing_entries = partition_existing(all_entries)
    for entry in missing_entries:
        append_skipped(entry["path"], "missing target file")
        log(f"SKIP {entry['path']} (missing target file)")
    completed = set(read_progress())
    pending = [entry for entry in all_entries if entry["path"] not in completed]
    batch = pending[: args.batch]

    processed_paths: list[str] = []
    blockers: list[str] = []
    status = "DONE" if not batch and not pending else "IN_PROGRESS"

    if batch:
        worker_count = 1 if args.dry_run else max(1, min(args.workers, len(batch)))
        log(f"Starting duplicate batch: {len(batch)} file(s), {worker_count} worker(s), timeout {args.timeout}s")
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(process_entry, entry, args.timeout, args.dry_run): entry
                for entry in batch
            }
            for future in concurrent.futures.as_completed(future_map):
                entry = future_map[future]
                try:
                    ok, _ = future.result()
                    if ok:
                        processed_paths.append(entry["path"])
                except Exception as exc:
                    blockers.append(f"{entry['path']}: {exc}")
                    log(f"FAILED {entry['path']}: {exc}")

    progress_lines = read_progress()
    last_progress = progress_lines[-1] if progress_lines else "(none)"
    remaining = len(all_entries) - len(set(progress_lines))
    if not batch and pending:
        status = "IN_PROGRESS"
    elif blockers:
        status = "BLOCKED"
    elif remaining == 0 and status != "BLOCKED":
        status = "DONE"
    elif processed_paths and status != "BLOCKED":
        status = "IN_PROGRESS"

    print()
    print("RECEIPT")
    print("-------")
    print(f"Files processed this run: {processed_paths}")
    print(f"Progress ledger last entry: {last_progress}")
    print(f"Output file record count: {len(progress_lines)}")
    print(f"Files remaining: {remaining}")
    print(f"Status: {status}")
    if blockers:
        print(f"Blocker (if BLOCKED): {' || '.join(blockers)}")
    return 0 if status != "BLOCKED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
