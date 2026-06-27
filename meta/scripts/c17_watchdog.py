#!/usr/bin/env python3
"""Unattended Campaign 17 epoch runner.

Runs one GPU training job at a time, evaluates every finished epoch, and polls
on a fixed interval so the campaign can continue while the workstation is away.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path("/home/aomukai/.unsloth/studio/unsloth_studio/bin/python")
REPORT_DIR = ROOT / "training/logs/campaign_17_reports"
EVAL_DIR = ROOT / "training/logs/grounding_eval"
SUMMARY = REPORT_DIR / "c17_watchdog_summary.jsonl"

PROBES = [
    "who are you?",
    "what is a dog?",
    "what does a dog look like?",
    "is a dog a machine?",
    "what is an airport used for?",
    "what does an airplane do?",
    "what is water?",
    "what is a tree?",
    "what happened at my school today?",
    "what is the name of this dog?",
]


@dataclass(frozen=True)
class Track:
    label: str
    corpus: Path
    prefix: str

    def checkpoint(self, epoch: int) -> Path:
        return ROOT / f"core/{self.prefix}_e{epoch}.pt"

    def train_log(self, epoch: int) -> Path:
        return REPORT_DIR / f"{self.prefix}_e{epoch}_train.log"

    def eval_report(self, epoch: int) -> Path:
        return EVAL_DIR / f"{self.prefix}_e{epoch}.md"

    def manual_report(self, epoch: int) -> Path:
        return REPORT_DIR / f"{self.prefix}_e{epoch}_manual_gate.md"


TRACKS = [
    Track(
        label="sorted",
        corpus=ROOT / "training/corpus/kernel_c17_ladder_1200_e1.jsonl",
        prefix="c17_ladder_1200",
    ),
    Track(
        label="contrast",
        corpus=ROOT / "training/corpus/kernel_c17_contrast_angle_1200_e1.jsonl",
        prefix="c17_contrast_angle_1200",
    ),
]


def log(message: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with (REPORT_DIR / "c17_watchdog.log").open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def run(cmd: list[str], *, env: dict[str, str] | None = None, stdout: Path | None = None) -> int:
    if stdout is None:
        return subprocess.run(cmd, cwd=ROOT, env=env).returncode
    stdout.parent.mkdir(parents=True, exist_ok=True)
    with stdout.open("w", encoding="utf-8") as handle:
        return subprocess.run(cmd, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT).returncode


def training_processes() -> list[str]:
    proc = subprocess.run(
        ["pgrep", "-af", "train.py --phase 0 --jsonl-data training/corpus/kernel_c17_"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    lines = [line for line in proc.stdout.splitlines() if "pgrep -af" not in line]
    return lines


def gpu_free_mib() -> int | None:
    proc = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        return None
    try:
        return int(proc.stdout.splitlines()[0].strip())
    except (IndexError, ValueError):
        return None


def eval_exists(track: Track, epoch: int) -> bool:
    return track.eval_report(epoch).exists()


def summary_exists(track: Track, epoch: int) -> bool:
    if not SUMMARY.exists():
        return False
    checkpoint = str(track.checkpoint(epoch).relative_to(ROOT))
    with SUMMARY.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("checkpoint") == checkpoint:
                return True
    return False


def eval_complete(track: Track, epoch: int) -> bool:
    return (
        eval_exists(track, epoch)
        and track.manual_report(epoch).exists()
        and summary_exists(track, epoch)
    )


def run_eval(track: Track, epoch: int) -> bool:
    ckpt = track.checkpoint(epoch)
    if not ckpt.exists():
        return False
    if eval_exists(track, epoch):
        run_manual_gate(track, epoch)
        summarize(track, epoch)
        return True
    log(f"eval {track.label} e{epoch}: {ckpt.relative_to(ROOT)}")
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "0"
    code = run(
        [
            str(PYTHON),
            "-u",
            "meta/scripts/eval_grounding.py",
            "--checkpoint",
            str(ckpt.relative_to(ROOT)),
            "--name",
            f"{track.prefix}_e{epoch}",
        ],
        env=env,
        stdout=REPORT_DIR / f"{track.prefix}_e{epoch}_eval.log",
    )
    if code != 0:
        log(f"eval failed for {track.label} e{epoch} with code {code}")
        return False
    run_manual_gate(track, epoch)
    summarize(track, epoch)
    return True


def run_manual_gate(track: Track, epoch: int) -> None:
    output = track.manual_report(epoch)
    if output.exists():
        return
    checkpoint_name = str(track.checkpoint(epoch).relative_to(ROOT))
    code = f"""
from inference import BDHInference
probes = {PROBES!r}
checkpoint = {checkpoint_name!r}
model = BDHInference(checkpoint, max_new_tokens=80, temperature=1.0, top_k=1)
print('# Manual Gate')
print()
print(f'- checkpoint: `{{checkpoint}}`')
print('- config: greedy, max_new_tokens=80')
for q in probes:
    prompt = f'[user]{{q}}\\n[Ninereeds]'
    print()
    print('## ' + q)
    print()
    print('```text')
    print(model.generate_text(prompt))
    print('```')
"""
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "0"
    run([str(PYTHON), "-c", code], env=env, stdout=output)


def parse_eval(track: Track, epoch: int) -> dict[str, object]:
    report = track.eval_report(epoch)
    text = report.read_text(encoding="utf-8", errors="replace") if report.exists() else ""
    pass_rate = re.search(r"pass_rate: `([^`]+)`", text)
    avg_score = re.search(r"avg_score: `([^`]+)`", text)
    return {
        "track": track.label,
        "epoch": epoch,
        "checkpoint": str(track.checkpoint(epoch).relative_to(ROOT)),
        "pass_rate": pass_rate.group(1) if pass_rate else None,
        "avg_score": float(avg_score.group(1)) if avg_score else None,
    }


def summarize(track: Track, epoch: int) -> None:
    if summary_exists(track, epoch):
        return
    item = parse_eval(track, epoch)
    with SUMMARY.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, sort_keys=True) + "\n")
    log(f"summary {track.label} e{epoch}: pass_rate={item['pass_rate']} avg={item['avg_score']}")


def latest_checkpoint_epoch(track: Track, max_epoch: int) -> int:
    latest = 0
    for epoch in range(1, max_epoch + 1):
        if track.checkpoint(epoch).exists():
            latest = epoch
    return latest


def train_epoch(track: Track, epoch: int) -> bool:
    resume = ROOT / "core/kernel_e1_focus_repair.pt" if epoch == 1 else track.checkpoint(epoch - 1)
    if not resume.exists():
        log(f"cannot train {track.label} e{epoch}: missing resume {resume.relative_to(ROOT)}")
        return False
    if track.checkpoint(epoch).exists():
        return True
    log(f"train {track.label} e{epoch}: resume {resume.relative_to(ROOT)}")
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "0"
    env["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"
    code = run(
        [
            str(PYTHON),
            "-u",
            "train.py",
            "--phase",
            "0",
            "--jsonl-data",
            str(track.corpus.relative_to(ROOT)),
            "--mask-instruction-loss",
            "--prompt-loss-weight",
            "0.0",
            "--prompt-tail-bytes",
            "96",
            "--block-size",
            "128",
            "--resume",
            str(resume.relative_to(ROOT)),
            "--output",
            str(track.checkpoint(epoch).relative_to(ROOT)),
            "--epochs",
            "1",
            "--amp-bf16",
            "--no-shuffle",
            "--lr",
            "1e-4",
            "--batch-size",
            "4",
        ],
        env=env,
        stdout=track.train_log(epoch),
    )
    if code != 0:
        log(f"train failed for {track.label} e{epoch} with code {code}")
        return False
    return True


def work_once(max_epoch: int, min_free_mib: int) -> bool:
    active = training_processes()
    if active:
        log(f"training already active; waiting ({len(active)} process lines)")
        return False

    for track in TRACKS:
        latest = latest_checkpoint_epoch(track, max_epoch)
        for epoch in range(1, latest + 1):
            if not eval_complete(track, epoch):
                return run_eval(track, epoch)

    for epoch in range(1, max_epoch + 1):
        for track in TRACKS:
            if not track.checkpoint(epoch).exists():
                free_mib = gpu_free_mib()
                if free_mib is not None and free_mib < min_free_mib:
                    log(f"GPU memory low; waiting before train ({free_mib} MiB free, need {min_free_mib} MiB)")
                    return False
                if train_epoch(track, epoch):
                    run_eval(track, epoch)
                return True
            if not eval_complete(track, epoch):
                return run_eval(track, epoch)

    log(f"complete: both tracks have checkpoints/evals through e{max_epoch}")
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-epoch", type=int, default=4)
    parser.add_argument("--poll-seconds", type=int, default=1800)
    parser.add_argument("--min-free-mib", type=int, default=5500)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    log(
        "watchdog start: "
        f"max_epoch={args.max_epoch}, poll_seconds={args.poll_seconds}, "
        f"min_free_mib={args.min_free_mib}"
    )
    while True:
        work_once(args.max_epoch, args.min_free_mib)
        all_done = all(
            track.checkpoint(epoch).exists() and eval_complete(track, epoch)
            for track in TRACKS
            for epoch in range(1, args.max_epoch + 1)
        )
        if all_done:
            log("watchdog finished all scheduled work")
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
