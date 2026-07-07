#!/usr/bin/env python3
"""Run a conservative MSM buffered micro-update.

This is the backend entry point documented in training/pipeline/update_artifact_schema.md.
It validates an MSM update manifest, checks approved training-turn records, converts them
to train.py's prompt/completion JSONL shape, and invokes train.py.

V1 intentionally supports one train.py epoch only. It treats the manifest's max_steps as
an upper bound on train.py micro-batches and chooses a batch size large enough to satisfy
that bound, capped by --max-batch-size. If the requested bound cannot be satisfied safely,
the script fails before training.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path("/home/aomukai/.unsloth/studio/unsloth_studio/bin/python")

EXPECTED_MANIFEST_VERSION = "msm_update_manifest_v1"
EXPECTED_TURN_VERSION = "msm_training_turn_v1"
ALLOWED_TURN_SOURCES = {
    "executor_proposed_correction",
    "executor_expected_answer",
    "deepseek_proposed_correction",
    "deepseek_expected_answer",
    "orchestrator_repair_line",
    "protected_anchor_replay",
}


class ValidationError(RuntimeError):
    pass


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def resolve(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{rel(path)} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"{rel(path)} must contain a JSON object.")
    return data


def require_string(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value:
        raise ValidationError(f"manifest field {key!r} must be a non-empty string.")
    return value


def require_bool(obj: dict[str, Any], key: str) -> bool:
    value = obj.get(key)
    if not isinstance(value, bool):
        raise ValidationError(f"manifest field {key!r} must be boolean.")
    return value


def require_int(obj: dict[str, Any], key: str, minimum: int = 0) -> int:
    value = obj.get(key)
    if not isinstance(value, int) or value < minimum:
        raise ValidationError(f"manifest field {key!r} must be an integer >= {minimum}.")
    return value


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("schema_version") != EXPECTED_MANIFEST_VERSION:
        raise ValidationError(
            f"schema_version must be {EXPECTED_MANIFEST_VERSION!r}, got {manifest.get('schema_version')!r}."
        )

    for key in (
        "update_id",
        "created_at",
        "parent_checkpoint",
        "output_checkpoint",
    ):
        require_string(manifest, key)

    source_sessions = manifest.get("source_sessions")
    if not isinstance(source_sessions, list) or not source_sessions or not all(isinstance(x, str) and x for x in source_sessions):
        raise ValidationError("source_sessions must be a non-empty list of strings.")

    approved_files = manifest.get("approved_training_files")
    if not isinstance(approved_files, list) or not approved_files or not all(isinstance(x, str) and x for x in approved_files):
        raise ValidationError("approved_training_files must be a non-empty list of strings.")

    require_int(manifest, "approved_turn_count", minimum=1)

    approval = manifest.get("approval")
    if not isinstance(approval, dict):
        raise ValidationError("approval must be an object.")
    if approval.get("orchestrator_approved") is not True:
        raise ValidationError("approval.orchestrator_approved must be true.")
    if not isinstance(approval.get("approved_by"), str) or not approval["approved_by"]:
        raise ValidationError("approval.approved_by must be a non-empty string.")
    if not isinstance(approval.get("approval_reason"), str) or not approval["approval_reason"]:
        raise ValidationError("approval.approval_reason must be a non-empty string.")
    if not isinstance(approval.get("human_approved"), bool):
        raise ValidationError("approval.human_approved must be boolean.")

    backend = manifest.get("update_backend")
    if not isinstance(backend, dict):
        raise ValidationError("update_backend must be an object.")
    if backend.get("name") != "buffered_micro_update":
        raise ValidationError("update_backend.name must be 'buffered_micro_update'.")
    if not isinstance(backend.get("command"), str) or not backend["command"]:
        raise ValidationError("update_backend.command must be a non-empty string.")
    lr = backend.get("learning_rate")
    if not isinstance(lr, (int, float)) or lr <= 0:
        raise ValidationError("update_backend.learning_rate must be > 0.")
    max_steps = backend.get("max_steps")
    if not isinstance(max_steps, int) or max_steps < 1:
        raise ValidationError("update_backend.max_steps must be an integer >= 1.")
    if not isinstance(backend.get("notes"), str):
        raise ValidationError("update_backend.notes must be a string.")

    if not isinstance(manifest.get("target_axes"), list):
        raise ValidationError("target_axes must be a list.")
    require_bool(manifest, "protected_anchors_required")


def validate_backend_command(manifest: dict[str, Any], manifest_path: Path) -> None:
    """Make update_backend.command a checked invocation contract, not decoration."""
    command = manifest["update_backend"]["command"]
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        raise ValidationError(f"update_backend.command is not shell-parseable: {exc}") from exc

    if not any(part.endswith("msm_micro_update.py") for part in parts):
        raise ValidationError("update_backend.command must invoke meta/scripts/msm_micro_update.py.")
    if "--manifest" not in parts:
        raise ValidationError("update_backend.command must include --manifest.")
    idx = parts.index("--manifest")
    if idx + 1 >= len(parts):
        raise ValidationError("update_backend.command has --manifest without a path.")
    command_manifest = resolve(parts[idx + 1]).resolve()
    if command_manifest != manifest_path.resolve():
        raise ValidationError(
            "update_backend.command --manifest path does not match the manifest being executed: "
            f"{rel(command_manifest)} != {rel(manifest_path)}"
        )


def validate_turn(obj: dict[str, Any], source_path: Path, line_no: int) -> None:
    prefix = f"{rel(source_path)}:{line_no}"
    if obj.get("schema_version") != EXPECTED_TURN_VERSION:
        raise ValidationError(f"{prefix}: schema_version must be {EXPECTED_TURN_VERSION!r}.")
    for key in ("session_id", "concept", "card_id", "turn_id", "prompt", "training_answer", "source"):
        if not isinstance(obj.get(key), str) or not obj[key]:
            raise ValidationError(f"{prefix}: {key!r} must be a non-empty string.")
    if obj["source"] not in ALLOWED_TURN_SOURCES:
        raise ValidationError(
            f"{prefix}: source must be one of {sorted(ALLOWED_TURN_SOURCES)}, got {obj['source']!r}."
        )
    if "target_failure" not in obj or not (obj["target_failure"] is None or isinstance(obj["target_failure"], str)):
        raise ValidationError(f"{prefix}: target_failure must be string or null.")
    executor_validated = obj.get("executor_validated")
    legacy_deepseek_validated = obj.get("deepseek_validated")
    if executor_validated is not True and legacy_deepseek_validated is not True:
        raise ValidationError(f"{prefix}: executor_validated must be true.")
    if obj.get("orchestrator_approved") is not True:
        raise ValidationError(f"{prefix}: orchestrator_approved must be true.")


def load_approved_turns(paths: list[Path]) -> list[dict[str, Any]]:
    turns: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            raise ValidationError(f"approved training file not found: {rel(path)}")
        with path.open(encoding="utf-8") as handle:
            for line_no, raw in enumerate(handle, start=1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValidationError(f"{rel(path)}:{line_no}: invalid JSON: {exc}") from exc
                if not isinstance(obj, dict):
                    raise ValidationError(f"{rel(path)}:{line_no}: record must be a JSON object.")
                validate_turn(obj, path, line_no)
                turns.append(obj)
    return turns


def write_train_jsonl(turns: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for turn in turns:
            record = {
                "prompt": turn["prompt"],
                "completion": turn["training_answer"],
                "source_session_id": turn["session_id"],
                "source_turn_id": turn["turn_id"],
                "concept": turn["concept"],
                "card_id": turn["card_id"],
                "target_failure": turn["target_failure"],
            }
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def compute_batch_size(n_turns: int, max_steps: int, max_batch_size: int) -> int:
    # train.py emits ceil(n_turns / batch_size) micro-batches for one epoch.
    batch_size = (n_turns + max_steps - 1) // max_steps
    if batch_size > max_batch_size:
        raise ValidationError(
            f"approved_turn_count={n_turns} with max_steps={max_steps} requires "
            f"batch_size={batch_size}, above --max-batch-size={max_batch_size}."
        )
    return max(batch_size, 1)


def build_train_command(
    manifest: dict[str, Any],
    train_jsonl: Path,
    batch_size: int,
    args: argparse.Namespace,
) -> list[str]:
    backend = manifest["update_backend"]
    cmd = [
        str(PYTHON),
        "-u",
        "train.py",
        "--phase",
        "0",
        "--jsonl-data",
        rel(train_jsonl),
        "--mask-instruction-loss",
        "--prompt-loss-weight",
        "0.0",
        "--prompt-tail-bytes",
        str(args.prompt_tail_bytes),
        "--block-size",
        str(args.block_size),
        "--resume",
        rel(resolve(manifest["parent_checkpoint"])),
        "--output",
        rel(resolve(manifest["output_checkpoint"])),
        "--skip-training-audit",
        "--epochs",
        "1",
        "--amp-bf16",
        "--no-shuffle",
        "--lr",
        str(backend["learning_rate"]),
        "--batch-size",
        str(batch_size),
        "--grad-accum-steps",
        "1",
        "--log-vram",
    ]
    if args.adam8bit:
        cmd.append("--adam8bit")
    return cmd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true", help="Validate and write train JSONL, but do not run train.py.")
    parser.add_argument("--max-batch-size", type=int, default=8)
    parser.add_argument("--block-size", type=int, default=128)
    parser.add_argument("--prompt-tail-bytes", type=int, default=96)
    parser.add_argument("--adam8bit", action="store_true")
    parser.add_argument("--allow-overwrite", action="store_true",
                        help="Allow output_checkpoint to already exist. Default is to fail before training.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    try:
        manifest = load_json(manifest_path)
        validate_manifest(manifest)
        validate_backend_command(manifest, manifest_path)

        parent = resolve(manifest["parent_checkpoint"])
        if not parent.exists():
            raise ValidationError(f"parent checkpoint not found: {rel(parent)}")
        output = resolve(manifest["output_checkpoint"])
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists() and not args.allow_overwrite:
            raise ValidationError(
                f"output checkpoint already exists: {rel(output)}. "
                "Use --allow-overwrite only after an explicit orchestrator decision."
            )

        approved_paths = [resolve(path) for path in manifest["approved_training_files"]]
        turns = load_approved_turns(approved_paths)
        expected_count = int(manifest["approved_turn_count"])
        if len(turns) != expected_count:
            raise ValidationError(
                f"approved_turn_count={expected_count} but approved files contain {len(turns)} records."
            )

        backend_max_steps = int(manifest["update_backend"]["max_steps"])
        batch_size = compute_batch_size(len(turns), backend_max_steps, args.max_batch_size)

        update_dir = manifest_path.parent
        train_jsonl = update_dir / "train_input.jsonl"
        write_train_jsonl(turns, train_jsonl)

        cmd = build_train_command(manifest, train_jsonl, batch_size, args)
        command_path = update_dir / "train_command.json"
        command_path.write_text(json.dumps({"cmd": cmd}, indent=2) + "\n", encoding="utf-8")
        backend_command_path = update_dir / "backend_command.json"
        backend_command_path.write_text(
            json.dumps({"argv": sys.argv, "manifest_command": manifest["update_backend"]["command"]}, indent=2)
            + "\n",
            encoding="utf-8",
        )

        print(f"Manifest: {rel(manifest_path)}")
        print(f"Approved turns: {len(turns)}")
        print(f"Train JSONL: {rel(train_jsonl)}")
        print(f"Batch size: {batch_size}")
        print(f"Output checkpoint: {rel(output)}")
        print("Command:")
        print(" ".join(cmd))

        if args.dry_run:
            print("Dry run complete; train.py not executed.")
            return 0

        env = os.environ.copy()
        env.setdefault("CUDA_VISIBLE_DEVICES", "0")
        env.setdefault("PYTORCH_ALLOC_CONF", "expandable_segments:True")
        log_path = update_dir / "train.log"
        with log_path.open("w", encoding="utf-8") as handle:
            code = subprocess.run(cmd, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT).returncode
        if code != 0:
            print(f"train.py failed with code {code}; log: {rel(log_path)}", file=sys.stderr)
            return code
        if not output.exists():
            print(f"train.py completed but output checkpoint is missing: {rel(output)}", file=sys.stderr)
            return 1
        print(f"Update complete: {rel(output)}")
        return 0
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
