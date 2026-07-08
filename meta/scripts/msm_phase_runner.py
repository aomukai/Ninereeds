#!/usr/bin/env python3
"""Run one cold-start MSM phase block.

This runner is for Phase 0/1 style cold-start bootstrapping:

generate examples -> train one bounded block -> optionally probe -> write compact report

It is intentionally separate from the later MSM session loop. Phase 0 cannot assume
Ninereeds can produce gradeable answers before frontloaded training examples have changed
weights.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MSM_ROOT = ROOT / "training/pipeline/msm"
REGISTRY_PATH = MSM_ROOT / "state/phase_registry.json"
UNSLOTH_PYTHON = Path("/home/aomukai/.unsloth/studio/unsloth_studio/bin/python")

PHASE0_WORDS = [
    "dog",
    "cat",
    "red",
    "blue",
    "sun",
    "tree",
    "water",
    "food",
    "book",
    "hand",
    "run",
    "sit",
    "look",
    "go",
    "yes",
    "no",
]

PHASE0_SENTENCES = [
    "A dog runs.",
    "A cat sits.",
    "The sun is up.",
    "A tree is green.",
    "Water is here.",
    "A book is open.",
]


class RunnerError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RunnerError(f"{rel(path)} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def train_python() -> str:
    env_value = os.environ.get("MSM_TRAIN_PYTHON")
    if env_value:
        return env_value
    if UNSLOTH_PYTHON.exists():
        return str(UNSLOTH_PYTHON)
    return sys.executable


def current_phase(registry: dict[str, Any]) -> str:
    phase_id = registry.get("current_phase_id")
    if not isinstance(phase_id, str) or not phase_id:
        raise RunnerError("phase_registry.current_phase_id must be a non-empty string")
    return phase_id


def next_block_id(phase_id: str) -> str:
    phase_dir = MSM_ROOT / "phase_blocks" / phase_id
    existing = sorted(phase_dir.glob(f"{phase_id}_block_*/block_report.json"))
    return f"{phase_id}_block_{len(existing) + 1:04d}"


def phase_parent(registry: dict[str, Any], explicit_parent: str | None) -> str:
    if explicit_parent:
        return explicit_parent
    parent = registry.get("checkpoint_policy", {}).get("current_parent")
    if isinstance(parent, str) and parent:
        return parent
    return "scratch"


def phase0_examples(count: int, seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed)
    rows: list[dict[str, str]] = []
    templates = ["say", "copy"]
    while len(rows) < count:
        choice = rng.choice(["word", "sentence"])
        if choice == "word":
            word = rng.choice(PHASE0_WORDS)
            verb = rng.choice(templates)
            rows.append({
                "prompt": f"[user] {verb} {word}\n[Ninereeds]",
                "completion": f" {word}.",
            })
        else:
            sentence = rng.choice(PHASE0_SENTENCES)
            rows.append({
                "prompt": "[user] write a short sentence\n[Ninereeds]",
                "completion": f" {sentence}",
            })
    return rows


def phase1_examples(count: int, seed: int) -> list[dict[str, str]]:
    # Placeholder allowlist sample. Later this should read the canonical allowlist.
    rng = random.Random(seed)
    rows: list[dict[str, str]] = []
    while len(rows) < count:
        word = rng.choice(PHASE0_WORDS)
        rows.append({
            "prompt": f"[user] the word is {word}\n[Ninereeds]",
            "completion": f" {word} is a word.",
        })
    return rows


def generate_frontload(phase_id: str, count: int, seed: int) -> list[dict[str, str]]:
    if phase_id == "phase_0_form":
        return phase0_examples(count, seed)
    if phase_id == "phase_1_word_form":
        return phase1_examples(count, seed)
    raise RunnerError(
        f"{phase_id} is not implemented in msm_phase_runner.py yet. "
        "Phase 0 and Phase 1 are the cold-start runner prerequisites."
    )


def build_train_command(
    *,
    jsonl_path: Path,
    output_checkpoint: Path,
    parent: str,
    args: argparse.Namespace,
) -> list[str]:
    cmd = [
        train_python(),
        "-u",
        "train.py",
        "--phase",
        "0",
        "--jsonl-data",
        rel(jsonl_path),
        "--mask-instruction-loss",
        "--prompt-loss-weight",
        "0.0",
        "--prompt-tail-bytes",
        str(args.prompt_tail_bytes),
        "--block-size",
        str(args.block_size),
        "--epochs",
        str(args.epochs),
        "--lr",
        str(args.lr),
        "--batch-size",
        str(args.batch_size),
        "--output",
        rel(output_checkpoint),
        "--skip-training-audit",
        "--seed",
        str(args.seed),
    ]
    if args.no_shuffle:
        cmd.append("--no-shuffle")
    if args.amp_bf16:
        cmd.append("--amp-bf16")
    if args.adam8bit:
        cmd.append("--adam8bit")
    if args.device:
        cmd.extend(["--device", args.device])
    if parent != "scratch":
        parent_path = ROOT / parent if not Path(parent).is_absolute() else Path(parent)
        if not parent_path.exists():
            raise RunnerError(f"parent checkpoint not found: {parent}")
        cmd.extend(["--resume", rel(parent_path)])
    return cmd


def run_train(cmd: list[str], stdout_path: Path) -> None:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("w", encoding="utf-8") as handle:
        proc = subprocess.run(cmd, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        raise RunnerError(f"train.py failed with exit code {proc.returncode}; see {rel(stdout_path)}")


def write_probe_manifest(path: Path, phase_id: str) -> None:
    if phase_id == "phase_0_form":
        probes = [
            {"prompt": "[user] say dog\n[Ninereeds]", "target": "word_copy"},
            {"prompt": "[user] say cat\n[Ninereeds]", "target": "word_copy"},
            {"prompt": "[user] write a short sentence\n[Ninereeds]", "target": "sentence_shape"},
        ]
    else:
        probes = [
            {"prompt": "[user] the word is dog\n[Ninereeds]", "target": "word_form"},
            {"prompt": "[user] the word is cat\n[Ninereeds]", "target": "word_form"},
        ]
    append_jsonl(path, probes)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase-id", default=None, help="Phase to run; defaults to phase_registry.current_phase_id")
    parser.add_argument("--parent", default=None, help="Parent checkpoint or 'scratch'. Defaults to registry checkpoint policy or scratch.")
    parser.add_argument("--examples", type=int, default=128, help="Frontload examples in this block.")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--block-size", type=int, default=128)
    parser.add_argument("--prompt-tail-bytes", type=int, default=64)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--device", default=None)
    parser.add_argument("--amp-bf16", action="store_true")
    parser.add_argument("--adam8bit", action="store_true")
    parser.add_argument("--no-shuffle", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Write artifacts and command, but do not run train.py.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.examples <= 0:
        raise RunnerError("--examples must be > 0")
    if args.prompt_tail_bytes >= args.block_size:
        raise RunnerError("--prompt-tail-bytes must be < --block-size")

    registry = load_json(REGISTRY_PATH)
    phase_id = args.phase_id or current_phase(registry)
    block_id = next_block_id(phase_id)
    block_dir = MSM_ROOT / "phase_blocks" / phase_id / block_id
    frontload_path = block_dir / "frontload.jsonl"
    probe_path = block_dir / "probes.jsonl"
    stdout_path = block_dir / "train_stdout.log"
    report_path = block_dir / "block_report.json"
    output_checkpoint = ROOT / "core/msm" / f"{block_id}.pt"
    parent = phase_parent(registry, args.parent)

    rows = generate_frontload(phase_id, args.examples, args.seed)
    append_jsonl(frontload_path, rows)
    write_probe_manifest(probe_path, phase_id)

    cmd = build_train_command(
        jsonl_path=frontload_path,
        output_checkpoint=output_checkpoint,
        parent=parent,
        args=args,
    )

    status = "planned"
    checkpoint_after: str | None = None
    metrics: dict[str, Any] = {
        "probe_execution": "not_implemented",
        "frontload_examples": len(rows),
    }
    gate_status = "not_evaluated"
    recommendation = "run_next_block_same_phase"
    notes = "Dry run only; train.py was not executed." if args.dry_run else None

    try:
        if not args.dry_run:
            run_train(cmd, stdout_path)
            if not output_checkpoint.exists():
                raise RunnerError(f"expected output checkpoint missing: {rel(output_checkpoint)}")
            status = "trained"
            checkpoint_after = rel(output_checkpoint)
            notes = "Training block completed. Probe execution is the next implementation step."
    except Exception as exc:
        status = "failed"
        gate_status = "blocked"
        recommendation = "blocked"
        notes = str(exc)

    report = {
        "schema_version": "msm_phase_block_report_v1",
        "phase_id": phase_id,
        "block_id": block_id,
        "created_at": utc_now(),
        "status": status,
        "checkpoint_before": parent,
        "checkpoint_after": checkpoint_after,
        "frontload_examples": len(rows),
        "train_command": cmd,
        "probe_command": None,
        "metrics": metrics,
        "gate_status": gate_status,
        "local_recommendation": recommendation,
        "artifacts": {
            "frontload_jsonl": rel(frontload_path),
            "probe_jsonl": rel(probe_path),
            "train_stdout": rel(stdout_path) if stdout_path.exists() else None,
            "report_json": rel(report_path),
        },
        "notes": notes,
    }
    write_json(report_path, report)
    print(json.dumps({"block_report": rel(report_path), "status": status, "train_command": shlex.join(cmd)}, indent=2))
    return 1 if status == "failed" else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RunnerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
