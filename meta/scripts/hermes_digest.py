#!/usr/bin/env python3
"""Build the read-only Hermes digest from MSM repository artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MSM = ROOT / "training/pipeline/msm"
STATE = MSM / "state"
SENTINELS = {
    "HUMAN_ATTENTION",
    "BLOCKED",
    "TRAINING_MACHINE_DOWN",
    "API_CREDITS_EXHAUSTED",
    "PROMOTION_REVIEW_REQUIRED",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"_error": "invalid_json", "path": rel(path)}
    return data if isinstance(data, dict) else {"_error": "not_object", "path": rel(path)}


def latest(pattern: str) -> Path | None:
    paths = [path for path in MSM.glob(pattern) if path.exists()]
    if not paths:
        return None
    return max(paths, key=lambda path: path.stat().st_mtime)


def find_sentinels() -> list[Path]:
    if not MSM.exists():
        return []
    return sorted(path for path in MSM.rglob("*") if path.is_file() and path.name in SENTINELS)


def sentinel_summary(path: Path) -> str:
    data = load_json(path)
    if data and "_error" not in data:
        reason = data.get("reason") or "no reason"
        requested = data.get("requested_action") or "no requested_action"
        return f"- {rel(path)}: {reason}; requested: {requested}"
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    return f"- {rel(path)}: {text[:200] if text else 'empty sentinel'}"


def format_or_none(value: Any) -> str:
    return "none" if value is None or value == "" else str(value)


def percent_or_none(value: Any) -> str:
    return "none" if value is None or value == "" else f"{value}%"


def report_card_line(path: Path | None) -> str:
    report = load_json(path)
    if not report:
        return "- none"
    scores = report.get("scores") if isinstance(report.get("scores"), dict) else {}
    recommendation = report.get("executor_recommendation") if isinstance(report.get("executor_recommendation"), dict) else {}
    return (
        f"- {rel(path)}: session={format_or_none(report.get('session_id'))}, "
        f"card={format_or_none(report.get('card_id'))}, "
        f"passed={format_or_none(scores.get('session_passed'))}, "
        f"requires_orchestrator={format_or_none(scores.get('requires_orchestrator'))}, "
        f"recommendation={format_or_none(recommendation.get('recommendation_type'))}"
    )


def block_report_line(path: Path | None) -> str:
    report = load_json(path)
    if not report:
        return "- none"
    return (
        f"- {rel(path)}: phase={format_or_none(report.get('phase_id'))}, "
        f"block={format_or_none(report.get('block_id'))}, "
        f"status={format_or_none(report.get('status'))}, "
        f"gate={format_or_none(report.get('gate_status'))}, "
        f"recommendation={format_or_none(report.get('local_recommendation'))}"
    )


def update_eval_line(path: Path | None) -> str:
    report = load_json(path)
    if not report:
        return "- none"
    decision = report.get("decision") if isinstance(report.get("decision"), dict) else {}
    return (
        f"- {rel(path)}: update={format_or_none(report.get('update_id'))}, "
        f"status={format_or_none(decision.get('status'))}, "
        f"reason={format_or_none(decision.get('reason'))}"
    )


def build_digest() -> str:
    orchestrator = load_json(STATE / "orchestrator_status.json") or {}
    brake = load_json(STATE / "codex_brake.json") or {}
    codex = load_json(STATE / "codex_status.json") or {}
    heartbeat = load_json(STATE / "trainbox_heartbeat.json")
    sentinels = find_sentinels()
    sentinel_lines = "\n".join(sentinel_summary(path) for path in sentinels) if sentinels else "- none"

    latest_session = latest("sessions/*/report_card.json")
    latest_block = latest("phase_blocks/*/*/block_report.json")
    latest_update = latest("updates/*/update_candidate_eval.json")

    return (
        "# Hermes MSM Digest\n\n"
        f"- Generated: {utc_now()}\n"
        f"- Next safe action: {format_or_none(orchestrator.get('next_safe_action'))}\n"
        f"- Wake reason: {format_or_none(orchestrator.get('wake_reason'))}\n"
        f"- Current phase: {format_or_none(orchestrator.get('current_phase_id'))}\n"
        f"- Phase gate: {format_or_none(orchestrator.get('phase_gate_status'))}\n"
        f"- Codex brake: {format_or_none(brake.get('action'))}\n"
        f"- Codex 5h left: {percent_or_none(codex.get('five_hour_percent_left'))}\n"
        f"- Codex weekly left: {percent_or_none(codex.get('weekly_percent_left'))}\n"
        f"- Codex projected exhaustion: {format_or_none(codex.get('projected_exhaustion'))}\n"
        f"- Trainbox heartbeat: {format_or_none(heartbeat.get('updated_at') if heartbeat else None)}\n"
        "\n## Sentinels\n\n"
        f"{sentinel_lines}\n"
        "\n## Latest Reports\n\n"
        f"{block_report_line(latest_block)}\n"
        f"{report_card_line(latest_session)}\n"
        f"{update_eval_line(latest_update)}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-file",
        type=Path,
        default=STATE / "hermes_digest.md",
        help="Write digest markdown here. Defaults to training/pipeline/msm/state/hermes_digest.md.",
    )
    parser.add_argument("--quiet", action="store_true", help="Do not print digest to stdout.")
    args = parser.parse_args()

    digest = build_digest()
    output = args.write_file if args.write_file.is_absolute() else ROOT / args.write_file
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(digest, encoding="utf-8")
    if not args.quiet:
        print(digest, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
