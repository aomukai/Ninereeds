#!/usr/bin/env python3
"""
Repair formatting/frame issues with opencode + DeepSeek v4 flash.

Queue-driven and resumable:
- reads training_data/phases/repair_formatting.txt
- groups multiple reasons per target file
- skips targets already listed in repair_progress_formatting.txt
- writes verified results back in place
- appends the progress ledger only after a confirmed write
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import shutil
import threading
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
QUEUE_PATH = REPO_ROOT / "training_data/phases/repair_formatting.txt"
PROGRESS_PATH = REPO_ROOT / "training_data/phases/repair_progress_formatting.txt"
SKIPPED_PATH = REPO_ROOT / "training_data/phases/repair_skipped_formatting.txt"
_opencode_which = shutil.which("opencode")
OPENCODE_BIN = Path(_opencode_which) if _opencode_which else (Path.home() / ".opencode/bin/opencode")
MODEL = "openrouter/deepseek/deepseek-v4-flash"
DEBUG_DIR = REPO_ROOT / "tmp/opencode_formatting_debug"
PROGRESS_LOCK = threading.Lock()
PRINT_LOCK = threading.Lock()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair formatting queue via opencode")
    parser.add_argument("--batch", type=int, default=6, help="Number of files to process")
    parser.add_argument("--workers", type=int, default=6, help="Parallel opencode workers")
    parser.add_argument("--dry-run", action="store_true", help="List pending files without editing")
    parser.add_argument("--timeout", type=int, default=300, help="Per-file timeout in seconds")
    parser.add_argument("--reset", action="store_true", help="Truncate progress file before starting")
    return parser.parse_args()


def log(msg: str) -> None:
    with PRINT_LOCK:
        print(msg, flush=True)


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_progress(path_str: str) -> None:
    with PROGRESS_LOCK:
        with PROGRESS_PATH.open("a", encoding="utf-8") as fh:
            fh.write(path_str + "\n")


def append_skipped(path_str: str, reason: str) -> None:
    with PROGRESS_LOCK:
        existing = {
            line.split("|", 1)[0].strip()
            for line in read_lines(SKIPPED_PATH)
            if "|" in line
        }
        if path_str in existing:
            return
        with SKIPPED_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"{path_str} | {reason}\n")


def parse_queue() -> list[dict]:
    entries_by_path: OrderedDict[str, dict] = OrderedDict()
    for raw_line in QUEUE_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or ".md" not in line or "|" not in line:
            continue
        parts = [part.strip() for part in line.split("|", 2)]
        if len(parts) != 3:
            continue
        path_str, issue_type, reason = parts
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
        if (REPO_ROOT / entry["path"]).exists():
            existing.append(entry)
        else:
            missing.append(entry)
    return existing, missing


def read_file(path_str: str) -> str:
    return (REPO_ROOT / path_str).read_text(encoding="utf-8")


def build_prompt(entry: dict, retry: bool = False, no_write: bool = False) -> str:
    path_str = entry["path"]
    current_content = read_file(path_str)
    reason_blob = "\n".join(f"- {reason}" for reason in entry["reasons"])
    retry_note = ""
    if retry:
        retry_note = (
            "Previous attempt returned non-file output.\n"
            "Return only the rewritten file text for this one file.\n"
            "Do not return a receipt. Do not explain anything.\n\n"
        )
    no_write_note = ""
    if no_write:
        no_write_note = "Do NOT use the write tool. Return only the corrected file text.\n\n"

    return f"""{retry_note}{no_write_note}Repair the target file so it matches a coherent Ninereeds training-file format.

Hard rules:
- Output ONLY the full corrected file contents.
- No commentary, no receipt, no markdown fences.
- Keep the target word/concept unless the queue reason clearly requires reframing the file.
- Fix all listed issues for this file in one pass.
- Prefer the normal local corpus shape already used by nearby files in the same phase.
- Keep one sentence per content line.
- Use concrete, grammatical English.
- Preserve `[user]` / `[Ninereeds]` training-pair format.
- The file must contain exactly 4 Q&A blocks, each with a [user] question and a [Ninereeds] answer containing 5-6 body lines plus a summary line.
- Follow the arc: appearance -> location -> behaviour -> use/effect across the 4 blocks.

Target file: {path_str}
Issue types: {", ".join(entry["issue_types"])}
Reasons:
{reason_blob}

Current file contents:
--- BEGIN TARGET ---
{current_content}
--- END TARGET ---
"""


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = None

def _get_api_key() -> str:
    global API_KEY
    if API_KEY is None:
        key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY not set")
        API_KEY = key
    return API_KEY


def _openrouter_model() -> str:
    return MODEL.replace("openrouter/", "")


def run_opencode(prompt: str, timeout: int) -> tuple[str, str]:
    import urllib.request
    import urllib.error

    api_key = _get_api_key()
    model = _openrouter_model()

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "temperature": 0.3,
    }).encode("utf-8")

    req = urllib.request.Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ninereeds",
        },
        method="POST",
    )

    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API error {exc.code}: {body[:500]}")

    raw_json = resp.read().decode("utf-8", errors="replace")
    data = json.loads(raw_json)
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError(f"API returned no choices: {raw_json[:500]}")
    content = choices[0].get("message", {}).get("content", "")
    if not content:
        raise RuntimeError(f"API returned empty content: {raw_json[:500]}")
    return content.strip(), raw_json


def normalize_response(text: str) -> str:
    cleaned = text.strip()
    if "[user]" in cleaned:
        cleaned = cleaned[cleaned.index("[user]") :]
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()
    lines = []
    for line in cleaned.splitlines():
        if line.strip() in {"=== END ===", "```"}:
            continue
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def looks_like_receipt(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("RECEIPT") or ("Files processed this run:" in stripped and "Status:" in stripped)


def verify_rewrite(path_str: str, content: str) -> None:
    if "[user]" not in content or "[Ninereeds]" not in content:
        raise RuntimeError(f"{path_str}: missing required tags after rewrite")
    if "```" in content:
        raise RuntimeError(f"{path_str}: stray code fence in output")
    if len(content.strip()) < 40:
        raise RuntimeError(f"{path_str}: rewritten content is unexpectedly short")

    lines = content.splitlines()
    blocks: list[list[str]] = []
    cur: list[str] = []
    for line in lines:
        if not line.strip():
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(line)
    if cur:
        blocks.append(cur)
    if not blocks:
        raise RuntimeError(f"{path_str}: no content blocks found")
    if len(blocks) != 4:
        raise RuntimeError(f"{path_str}: expected 4 blocks, found {len(blocks)}")

    for bi, block in enumerate(blocks, 1):
        if len(block) < 3:
            raise RuntimeError(f"{path_str}: block {bi} is too short")
        if not block[0].startswith("[user]") or not block[1].startswith("[Ninereeds]"):
            raise RuntimeError(f"{path_str}: block {bi} missing standard headers")
        if block[1].count(".") != 1:
            raise RuntimeError(f"{path_str}: block {bi} opener line must contain exactly one sentence")
        for line in block[2:]:
            if line.startswith("[user]") or line.startswith("[Ninereeds]"):
                raise RuntimeError(f"{path_str}: block {bi} contains nested tag lines")
            if line.count(".") != 1:
                raise RuntimeError(f"{path_str}: content line must contain exactly one sentence")


def process_entry(entry: dict, timeout: int, dry_run: bool) -> tuple[bool, str]:
    path_str = entry["path"]
    if dry_run:
        log(f"[DRY RUN] {path_str}")
        for reason in entry["reasons"]:
            log(f"  - {reason}")
        return True, "dry-run"

    # Save original content for potential restore
    original_content = read_file(path_str)

    prompts = [
        build_prompt(entry, retry=False, no_write=True),
        build_prompt(entry, retry=True, no_write=True),
    ]
    response = ""
    raw = ""
    new_content = ""
    last_error: Exception | None = None

    for prompt in prompts:
        response, raw = run_opencode(prompt, timeout=timeout)
        if looks_like_receipt(response):
            last_error = RuntimeError(f"{path_str}: model returned receipt text instead of file contents")
            continue
        new_content = normalize_response(response)
        # The model may have used the write tool; read file from disk
        on_disk = (REPO_ROOT / path_str).read_text(encoding="utf-8")
        try:
            verify_rewrite(path_str, on_disk)
            # File on disk is valid; write our normalized version
            if new_content and "[user]" in new_content:
                (REPO_ROOT / path_str).write_text(new_content, encoding="utf-8")
            last_error = None
            break
        except Exception as exc:
            # On-disk file is bad; try the normalized version
            try:
                verify_rewrite(path_str, new_content)
                (REPO_ROOT / path_str).write_text(new_content, encoding="utf-8")
                last_error = None
                break
            except Exception:
                # Both failed; restore original and try next prompt
                (REPO_ROOT / path_str).write_text(original_content, encoding="utf-8")
                last_error = exc

    if last_error is not None:
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        base = Path(path_str).name
        (DEBUG_DIR / f"{base}.response.txt").write_text(new_content if new_content else response, encoding="utf-8")
        (DEBUG_DIR / f"{base}.events.jsonl").write_text(raw, encoding="utf-8")
        # Restore original on final failure
        (REPO_ROOT / path_str).write_text(original_content, encoding="utf-8")
        raise last_error

    append_progress(path_str)
    log(f"OK {path_str}")
    return True, "ok"


def main() -> int:
    args = parse_args()
    if not OPENCODE_BIN.exists():
        raise SystemExit(f"ERROR: opencode binary not found at {OPENCODE_BIN}")
    if not QUEUE_PATH.exists():
        raise SystemExit(f"ERROR: queue not found at {QUEUE_PATH}")

    if args.reset:
        PROGRESS_PATH.write_text("", encoding="utf-8")
        log("Progress file reset to empty")

    all_entries = parse_queue()
    all_entries, missing_entries = partition_existing(all_entries)
    for entry in missing_entries:
        append_skipped(entry["path"], "missing target file")
        log(f"SKIP {entry['path']} (missing target file)")

    completed = set(read_lines(PROGRESS_PATH))
    pending = [entry for entry in all_entries if entry["path"] not in completed]
    batch = pending[: args.batch]
    processed_paths: list[str] = []
    blockers: list[str] = []

    if batch:
        worker_count = 1 if args.dry_run else max(1, min(args.workers, len(batch)))
        log(f"Starting formatting batch: {len(batch)} file(s), {worker_count} worker(s), timeout {args.timeout}s")
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

    progress_lines = read_lines(PROGRESS_PATH)
    last_progress = progress_lines[-1] if progress_lines else "(none)"
    remaining = max(0, len(all_entries) - len(set(progress_lines)))
    status = "DONE" if remaining == 0 and not blockers else "IN_PROGRESS"
    if blockers:
        status = "BLOCKED"

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
