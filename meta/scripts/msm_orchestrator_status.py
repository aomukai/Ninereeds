#!/usr/bin/env python3
"""Print deterministic startup status for the stateless MSM orchestrator."""

from __future__ import annotations

import json
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


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"_error": "invalid_json", "path": rel(path)}
    return data if isinstance(data, dict) else {"_error": "not_object", "path": rel(path)}


def latest(paths: list[Path]) -> Path | None:
    existing = [p for p in paths if p.exists()]
    if not existing:
        return None
    return max(existing, key=lambda p: p.stat().st_mtime)


def find_latest(pattern: str) -> Path | None:
    return latest(list(MSM.glob(pattern)))


def find_sentinels() -> list[str]:
    if not MSM.exists():
        return []
    found: list[str] = []
    for path in MSM.rglob("*"):
        if path.is_file() and path.name in SENTINELS:
            found.append(rel(path))
    return sorted(found)


def infer_next_action(
    *,
    registry: dict[str, Any] | None,
    config: dict[str, Any] | None,
    brake: dict[str, Any] | None,
    sentinels: list[str],
    latest_block_report: dict[str, Any] | None,
) -> tuple[str, str]:
    if sentinels:
        return "stop", "sentinel_present"
    if brake and brake.get("action") in {"pause_until_reset", "blocked_unknown_reset"}:
        return "stop", f"codex_brake:{brake.get('action')}"
    if registry is None:
        return "create_or_repair_phase_registry", "phase_registry_missing"
    if config is None:
        return "create_orchestrator_config", "orchestrator_config_missing"
    if latest_block_report is None:
        return "run_phase_block", "no_block_yet"
    status = latest_block_report.get("status")
    gate_status = latest_block_report.get("gate_status")
    recommendation = latest_block_report.get("local_recommendation")
    if status == "failed" or gate_status == "blocked":
        return "escalate_or_repair_block", "block_failed"
    if recommendation == "phase_gate_review" or gate_status == "met":
        return "review_phase_gate", "gate_review"
    return "run_or_wait_next_block", "block_finished"


def main() -> int:
    registry_path = STATE / "phase_registry.json"
    config_path = STATE / "orchestrator_config.json"
    brake_path = STATE / "codex_brake.json"
    registry = load_json(registry_path)
    config = load_json(config_path)
    brake = load_json(brake_path)
    current_phase = registry.get("current_phase_id") if registry else None

    latest_block_path = None
    if isinstance(current_phase, str) and current_phase:
        latest_block_path = find_latest(f"phase_blocks/{current_phase}/*/block_report.json")
    if latest_block_path is None:
        latest_block_path = find_latest("phase_blocks/*/*/block_report.json")
    latest_block_report = load_json(latest_block_path) if latest_block_path else None

    latest_session = find_latest("sessions/*/report_card.json")
    latest_update = find_latest("updates/*/update_candidate_eval.json")
    sentinels = find_sentinels()
    next_action, wake_reason = infer_next_action(
        registry=registry,
        config=config,
        brake=brake,
        sentinels=sentinels,
        latest_block_report=latest_block_report,
    )

    summary = {
        "schema_version": "msm_orchestrator_status_v1",
        "regime": registry.get("regime") if registry else None,
        "current_phase_id": current_phase,
        "phase_gate_status": (
            registry.get("phases", {}).get(current_phase, {}).get("gate_status")
            if registry and isinstance(current_phase, str)
            else None
        ),
        "orchestrator_config_present": config is not None,
        "codex_brake_action": brake.get("action") if brake else None,
        "sentinels": sentinels,
        "latest_block_report": rel(latest_block_path) if latest_block_path else None,
        "latest_block_status": latest_block_report.get("status") if latest_block_report else None,
        "latest_block_gate_status": latest_block_report.get("gate_status") if latest_block_report else None,
        "latest_session_report": rel(latest_session) if latest_session else None,
        "latest_update_eval": rel(latest_update) if latest_update else None,
        "wake_reason": wake_reason,
        "next_safe_action": next_action,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
