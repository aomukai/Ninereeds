#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
WIKI_DIR = REPO_ROOT / "training_data" / "wiki"
TODO_PATH = WIKI_DIR / "02_wiki_implementation_todo.md"
LOG_PATH = WIKI_DIR / "wiki_implementation_run_log.md"
MAX_TURNS = "18"

CHECKBOX_RE = re.compile(r"^(?P<prefix>\s*(?:\d+\.|[-*])\s+)\[(?P<mark>[ xX])\]\s+(?P<item>.+?)\s*$")
RATE_LIMIT_PATTERNS = [
    "rate limit",
    "429",
    "too many requests",
    "usage limit",
    "overloaded",
    "try again later",
    "exceeded your current quota",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def find_todo_file() -> Path:
    if TODO_PATH.exists():
        return TODO_PATH
    raise FileNotFoundError(f"Could not find wiki implementation todo file: {TODO_PATH}")


def find_next_unchecked(todo_path: Path) -> Optional[dict]:
    lines = todo_path.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        match = CHECKBOX_RE.match(line)
        if match and match.group("mark") == " ":
            return {
                "line_number": index + 1,
                "raw_line": line,
                "item": match.group("item").strip(),
            }
    return None


def append_log(status: str, todo_path: Path, item: Optional[str], summary: str, changed_files: Optional[list[str]] = None, extra: Optional[str] = None) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_PATH.exists():
        LOG_PATH.write_text("# Wiki Implementation Cron Log\n\n", encoding="utf-8")

    lines = [
        f"## {utc_now()} — {status}",
        f"- todo file: `{todo_path.relative_to(REPO_ROOT)}`",
        f"- item: `{item}`" if item else "- item: none",
        f"- summary: {summary}",
    ]
    if changed_files is not None:
        if changed_files:
            lines.append("- changed files:")
            lines.extend(f"  - `{path}`" for path in changed_files)
        else:
            lines.append("- changed files: none")
    if extra:
        lines.append("- details:")
        for line in extra.strip().splitlines():
            lines.append(f"  {line}")
    lines.append("")

    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        capture_output=True,
    )


def is_rate_limited(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in RATE_LIMIT_PATTERNS)


def parse_claude_json(stdout: str) -> dict:
    return json.loads(stdout)


def get_repo_state() -> set[str]:
    result = run(["git", "status", "--short", "--untracked-files=all"], REPO_ROOT)
    files: set[str] = set()
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        files.add(line[3:].strip() if len(line) >= 4 else line.strip())
    return files


def build_prompt(todo_path: Path, item: str) -> str:
    return f"""
You are implementing one wiki backlog item inside the BDH Cognitive OS repository.

Repository root: {REPO_ROOT}
Selected todo item: {item}
Todo file: {todo_path}

Mandatory instructions:
- Read and follow AGENTS.md, README.md, and docs/wiki.md before editing.
- Implement ONLY the selected todo item above.
- Update the appropriate wiki file or files under training_data/wiki/.
- Update the todo file by marking the selected item as checked and add a short Notes line describing what you implemented.
- Do not modify bdh.py or anything under core/.
- Do not commit, push, or create branches.
- Keep edits minimal, explicit, and reproducible.
- If supporting context is needed, you may read wiki_category_backlog.md and level1_finish_and_level2_start_plan.md.
- After finishing, print a concise final report in exactly this format:

STATUS: success
SUMMARY: <one short paragraph>
FILES:
- path/to/file1
- path/to/file2

If implementation is blocked for a non-rate-limit reason, print:

STATUS: blocked
SUMMARY: <reason>
FILES:
- none
""".strip()


def main() -> int:
    try:
        todo_path = find_todo_file()
    except FileNotFoundError as exc:
        append_log("missing-todo", TODO_PATH, None, str(exc))
        print(str(exc))
        return 1

    next_item = find_next_unchecked(todo_path)
    if not next_item:
        summary = "No unchecked wiki implementation items were found."
        append_log("no-op", todo_path, None, summary)
        print(summary)
        return 0

    item = next_item["item"]
    prompt = build_prompt(todo_path, item)
    before_state = get_repo_state()
    command = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "json",
        "--permission-mode",
        "bypassPermissions",
        "--allowedTools",
        "Read,Edit,Write,Bash",
        "--max-turns",
        MAX_TURNS,
    ]
    result = run(command, REPO_ROOT)
    combined_output = (result.stdout or "") + "\n" + (result.stderr or "")

    if is_rate_limited(combined_output):
        summary = "Claude Code hit a rate limit. Skipping this run and retrying next hour."
        append_log("rate-limited-skip", todo_path, item, summary, extra=combined_output[-4000:])
        print(summary)
        return 0

    if result.returncode != 0:
        summary = f"Claude Code failed with exit code {result.returncode}."
        append_log("error", todo_path, item, summary, extra=combined_output[-4000:])
        print(summary)
        print(combined_output)
        return result.returncode

    try:
        payload = parse_claude_json(result.stdout)
        claude_text = payload.get("result", "").strip()
    except json.JSONDecodeError:
        claude_text = result.stdout.strip()

    after_state = get_repo_state()
    changed_files = sorted(after_state - before_state)
    status_match = re.search(r"^STATUS:\s*(.+)$", claude_text, re.MULTILINE)
    summary_match = re.search(r"^SUMMARY:\s*(.+)$", claude_text, re.MULTILINE)
    status = status_match.group(1).strip() if status_match else "completed"
    summary = summary_match.group(1).strip() if summary_match else "Claude Code completed the run."

    append_log(status, todo_path, item, summary, changed_files=changed_files, extra=claude_text[-4000:])
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
