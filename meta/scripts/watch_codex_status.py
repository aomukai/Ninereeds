#!/usr/bin/env python3
"""Passive Codex TUI status watcher for the MSM autonomous loop.

This script observes a tmux pane running Codex, parses visible status rate-limit text when
available, and writes deterministic state files under training/pipeline/msm/state. It never sends
input to Codex.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

ACTION_CONTINUE = "continue"
ACTION_CONSERVATIVE = "conservative_mode"
ACTION_FINISH_CURRENT = "finish_current_only"
ACTION_PAUSE = "pause_until_reset"
ACTION_BLOCKED_UNKNOWN = "blocked_unknown_reset"

ALLOWED_ACTIONS = {
    ACTION_CONTINUE,
    ACTION_CONSERVATIVE,
    ACTION_FINISH_CURRENT,
    ACTION_PAUSE,
    ACTION_BLOCKED_UNKNOWN,
}


def now_local() -> dt.datetime:
    return dt.datetime.now().astimezone().replace(microsecond=0)


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def capture_tmux(session: str, lines: int) -> str:
    cmd = ["tmux", "capture-pane", "-t", session, "-p", "-S", f"-{lines}"]
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"tmux capture-pane failed with exit {proc.returncode}")
    return proc.stdout


def parse_percent_left(text: str, label_patterns: list[str]) -> tuple[int | None, str | None]:
    for label in label_patterns:
        pattern = re.compile(
            rf"{label}[^%\n\r]{{0,120}}?(\d{{1,3}})\s*%\s*(?:left|remaining)"
            rf"(?:[^()\n\r]{{0,80}}?\(?\s*resets?\s+([^)'\n\r]+)\)?)?",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if match:
            left = max(0, min(100, int(match.group(1))))
            reset = match.group(2).strip(" .") if match.group(2) else None
            return left, reset
    return None, None


def parse_reset_at(reset_text: str | None, now: dt.datetime) -> str | None:
    if not reset_text:
        return None

    text = reset_text.strip()
    time_match = re.search(r"\b(\d{1,2}):(\d{2})\b", text)
    if not time_match:
        return None

    hour = int(time_match.group(1))
    minute = int(time_match.group(2))
    if hour > 23 or minute > 59:
        return None

    month_match = re.search(
        r"\bon\s+(\d{1,2})\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b",
        text,
        re.IGNORECASE,
    )
    if month_match:
        months = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }
        day = int(month_match.group(1))
        month = months[month_match.group(2).lower()]
        year = now.year
        candidate = now.replace(year=year, month=month, day=day, hour=hour, minute=minute, second=0)
        if candidate < now - dt.timedelta(days=1):
            candidate = candidate.replace(year=year + 1)
        return candidate.isoformat()

    candidate = now.replace(hour=hour, minute=minute, second=0)
    if candidate <= now:
        candidate += dt.timedelta(days=1)
    return candidate.isoformat()


def action_for_usage(highest_used: int | None, parse_ok: bool) -> str:
    if not parse_ok or highest_used is None:
        return ACTION_BLOCKED_UNKNOWN
    if highest_used >= 90:
        return ACTION_PAUSE
    if highest_used >= 85:
        return ACTION_FINISH_CURRENT
    if highest_used >= 70:
        return ACTION_CONSERVATIVE
    return ACTION_CONTINUE


def apply_hysteresis(action: str, existing_brake: dict[str, Any] | None, now: dt.datetime) -> str:
    if not existing_brake:
        return action
    if existing_brake.get("action") != ACTION_PAUSE:
        return action
    reset_raw = existing_brake.get("reset_at")
    if not isinstance(reset_raw, str) or not reset_raw:
        return action
    try:
        reset_at = dt.datetime.fromisoformat(reset_raw)
    except ValueError:
        return action
    if reset_at > now and action in {ACTION_CONTINUE, ACTION_CONSERVATIVE, ACTION_FINISH_CURRENT}:
        return ACTION_PAUSE
    return action


def calculate_last_hour_delta(current_used: int | None, previous_status: dict[str, Any] | None, now: dt.datetime) -> int | None:
    if current_used is None or not previous_status:
        return None
    previous_used = previous_status.get("highest_percent_used")
    previous_time = previous_status.get("updated_at")
    if not isinstance(previous_used, int) or not isinstance(previous_time, str):
        return None
    try:
        previous_at = dt.datetime.fromisoformat(previous_time)
    except ValueError:
        return None
    elapsed_hours = max((now - previous_at).total_seconds() / 3600.0, 0.001)
    delta = current_used - previous_used
    if delta < 0:
        return 0
    return round(delta / elapsed_hours)


def projected_exhaustion(highest_used: int | None, last_hour_delta: int | None) -> str:
    if highest_used is None or last_hour_delta is None:
        return "unknown"
    if highest_used >= 90:
        return "danger"
    if last_hour_delta >= 10 or highest_used >= 85:
        return "danger"
    if last_hour_delta >= 5 or highest_used >= 70:
        return "warning"
    return "safe"


def write_blocked_sentinel(repo: Path, reason: str, now: dt.datetime) -> None:
    sentinel = repo / "training/pipeline/msm/BLOCKED"
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    if sentinel.exists():
        return
    body = {
        "created_at": now.isoformat(),
        "source": "codex_status_watchdog",
        "reason": reason,
        "requested_action": "Inspect visible Codex status parsing and update training/pipeline/msm/state/codex_brake.json.",
    }
    write_json(sentinel, body)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT, help="Repository root. Defaults to this script's repository.")
    parser.add_argument("--tmux-session", default="codex", help="tmux target passed to capture-pane.")
    parser.add_argument("--capture-lines", type=int, default=120, help="Number of trailing tmux pane lines to capture.")
    parser.add_argument("--snapshot-file", type=Path, help="Read an existing pane snapshot instead of invoking tmux.")
    parser.add_argument("--no-sentinel", action="store_true", help="Do not write BLOCKED on blocked_unknown_reset.")
    args = parser.parse_args()

    repo = args.repo.resolve()
    state = repo / "training/pipeline/msm/state"
    snap_path = state / "codex_pane_snapshot.txt"
    status_json = state / "codex_status.json"
    status_md = state / "codex_status.md"
    brake_json = state / "codex_brake.json"

    now = now_local()
    previous_status = read_json(status_json)
    existing_brake = read_json(brake_json)

    if args.snapshot_file:
        text = args.snapshot_file.read_text(encoding="utf-8", errors="ignore")
    else:
        text = capture_tmux(args.tmux_session, args.capture_lines)

    state.mkdir(parents=True, exist_ok=True)
    snap_path.write_text(text, encoding="utf-8")

    five_left, five_reset = parse_percent_left(text, [r"5\s*h(?:our)?(?:\s+limit)?", r"five[-\s]?hour"])
    weekly_left, weekly_reset = parse_percent_left(text, [r"weekly(?:\s+limit)?", r"week(?:ly)?"])

    five_used = 100 - five_left if five_left is not None else None
    weekly_used = 100 - weekly_left if weekly_left is not None else None
    used_values = [value for value in (five_used, weekly_used) if value is not None]
    highest = max(used_values) if used_values else None
    parse_ok = bool(used_values)
    last_hour_delta = calculate_last_hour_delta(highest, previous_status, now)
    projection = projected_exhaustion(highest, last_hour_delta)

    action = apply_hysteresis(action_for_usage(highest, parse_ok), existing_brake, now)
    reset_source = five_reset if five_used == highest else weekly_reset
    reset_at = parse_reset_at(reset_source, now)

    status = {
        "updated_at": now.isoformat(),
        "source": "tmux capture-pane of Codex TUI" if not args.snapshot_file else str(args.snapshot_file),
        "parse_ok": parse_ok,
        "five_hour_percent_left": five_left,
        "five_hour_resets": five_reset,
        "weekly_percent_left": weekly_left,
        "weekly_resets": weekly_reset,
        "five_hour_percent_used": five_used,
        "weekly_percent_used": weekly_used,
        "highest_percent_used": highest,
        "last_hour_delta_used": last_hour_delta,
        "projected_exhaustion": projection,
    }
    brake = {
        "updated_at": now.isoformat(),
        "source": "codex_status_watchdog",
        "action": action,
        "reason": "Codex usage threshold policy" if action != ACTION_BLOCKED_UNKNOWN else "Codex rate-limit status parse failed",
        "reset_at": reset_at,
        "five_hour_percent_left": five_left,
        "weekly_percent_left": weekly_left,
        "highest_percent_used": highest,
    }

    if brake["action"] not in ALLOWED_ACTIONS:
        raise RuntimeError(f"invalid brake action: {brake['action']}")

    write_json(status_json, status)
    write_json(brake_json, brake)
    status_md.write_text(
        "# Codex Status\n\n"
        f"- Updated: {status['updated_at']}\n"
        f"- Parse OK: {status['parse_ok']}\n"
        f"- 5h limit: {five_used}% used / {five_left}% left, resets {five_reset}\n"
        f"- Weekly limit: {weekly_used}% used / {weekly_left}% left, resets {weekly_reset}\n"
        f"- Last hour: {last_hour_delta}% used\n"
        f"- Projected exhaustion: {projection}\n"
        f"- Brake action: {action}\n",
        encoding="utf-8",
    )

    if action == ACTION_BLOCKED_UNKNOWN and not args.no_sentinel:
        write_blocked_sentinel(repo, "Codex rate-limit reset could not be parsed.", now)
    if action == ACTION_BLOCKED_UNKNOWN:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
