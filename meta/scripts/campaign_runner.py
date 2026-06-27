#!/usr/bin/env python3
"""Goal-oriented campaign runner with adaptive VRAM training profiles.

This runner is intentionally conservative:

- one train process at a time
- checkpoint/eval/manual-gate after every epoch
- resume by checking existing checkpoint and eval files
- before every train run, inspect free VRAM and choose train parameters
- if a run OOMs, retry once with the next smaller profile

The default config continues the current Campaign 17 sorted-vs-contrast tracks.
Later configs can add chunk, cluster, contrast-review, and repair corpora as
separate stages without changing the runner.
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
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PYTHON = Path("/home/aomukai/.unsloth/studio/unsloth_studio/bin/python")
REPORT_DIR = ROOT / "training/logs/campaign_17_reports"
EVAL_DIR = ROOT / "training/logs/grounding_eval"
SUMMARY = REPORT_DIR / "campaign_runner_summary.jsonl"

DEFAULT_PROBES = [
    "who are you?",
    "what is your name?",
    "what is a dog?",
    "what does a dog look like?",
    "is a dog a machine?",
    "what is an airport used for?",
    "what does an airplane do?",
    "how does an airplane work?",
    "what is water?",
    "what is a tree?",
    "what happened at my school today?",
    "what is the name of this dog?",
]


@dataclass(frozen=True)
class TrainProfile:
    name: str
    min_free_mib: int
    batch_size: int
    grad_accum_steps: int
    adam8bit: bool

    def args(self) -> list[str]:
        out = [
            "--batch-size",
            str(self.batch_size),
            "--grad-accum-steps",
            str(self.grad_accum_steps),
        ]
        if self.adam8bit:
            out.append("--adam8bit")
        return out


PROFILES = [
    TrainProfile("full", min_free_mib=5500, batch_size=4, grad_accum_steps=1, adam8bit=False),
    TrainProfile("medium", min_free_mib=3800, batch_size=2, grad_accum_steps=2, adam8bit=True),
    TrainProfile("low", min_free_mib=2500, batch_size=1, grad_accum_steps=4, adam8bit=True),
]


@dataclass(frozen=True)
class Stage:
    label: str
    corpus: Path
    prefix: str
    base: Path
    max_epoch: int
    order: int
    lr: float = 1e-4

    def checkpoint(self, epoch: int) -> Path:
        return ROOT / f"core/{self.prefix}_e{epoch}.pt"

    def train_log(self, epoch: int) -> Path:
        return REPORT_DIR / f"{self.prefix}_e{epoch}_train.log"

    def eval_report(self, epoch: int) -> Path:
        return EVAL_DIR / f"{self.prefix}_e{epoch}.md"

    def manual_report(self, epoch: int) -> Path:
        return REPORT_DIR / f"{self.prefix}_e{epoch}_manual_gate.md"

    def suite_eval_report(self, epoch: int, suite_name: str) -> Path:
        return EVAL_DIR / f"{self.prefix}_e{epoch}_{suite_name}.md"

    def resume_checkpoint(self, epoch: int) -> Path:
        return self.base if epoch == 1 else self.checkpoint(epoch - 1)


@dataclass(frozen=True)
class EvalSuite:
    name: str
    tests: Path | None = None


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def log(message: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with (REPORT_DIR / "campaign_runner.log").open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def run(cmd: list[str], *, env: dict[str, str] | None = None, stdout: Path | None = None) -> int:
    if stdout is None:
        return subprocess.run(cmd, cwd=ROOT, env=env).returncode
    stdout.parent.mkdir(parents=True, exist_ok=True)
    with stdout.open("w", encoding="utf-8") as handle:
        return subprocess.run(cmd, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT).returncode


def active_training() -> list[str]:
    proc = subprocess.run(
        ["pgrep", "-af", "train.py --phase 0"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return [line for line in proc.stdout.splitlines() if "pgrep -af" not in line]


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


def choose_profile() -> TrainProfile | None:
    free = gpu_free_mib()
    if free is None:
        log("could not read GPU memory; using low profile")
        return PROFILES[-1]
    for profile in PROFILES:
        if free >= profile.min_free_mib:
            log(
                "VRAM profile "
                f"{profile.name}: {free} MiB free, batch={profile.batch_size}, "
                f"grad_accum={profile.grad_accum_steps}, adam8bit={profile.adam8bit}"
            )
            return profile
    log(f"VRAM too low for training: {free} MiB free, need {PROFILES[-1].min_free_mib} MiB")
    return None


def wait_for_vram(min_free_mib: int, poll_seconds: int, purpose: str) -> None:
    while True:
        free = gpu_free_mib()
        if free is None or free >= min_free_mib:
            return
        log(f"VRAM too low for {purpose}: {free} MiB free, need {min_free_mib} MiB")
        time.sleep(poll_seconds)


def log_has_oom(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace").lower()
    return "outofmemoryerror" in text or "out of memory" in text or "cuda out of memory" in text


def eval_exists(stage: Stage, epoch: int) -> bool:
    return stage.eval_report(epoch).exists()


def summary_exists(stage: Stage, epoch: int) -> bool:
    if not SUMMARY.exists():
        return False
    checkpoint = rel(stage.checkpoint(epoch))
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


def suite_summary_exists(stage: Stage, epoch: int, suite: EvalSuite) -> bool:
    if not SUMMARY.exists():
        return False
    checkpoint = rel(stage.checkpoint(epoch))
    with SUMMARY.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("checkpoint") == checkpoint and item.get("suite") == suite.name:
                return True
    return False


def suite_eval_complete(stage: Stage, epoch: int, suite: EvalSuite) -> bool:
    return stage.suite_eval_report(epoch, suite.name).exists() and suite_summary_exists(stage, epoch, suite)


def eval_complete(stage: Stage, epoch: int, suites: list[EvalSuite]) -> bool:
    return (
        eval_exists(stage, epoch)
        and stage.manual_report(epoch).exists()
        and summary_exists(stage, epoch)
        and all(suite_eval_complete(stage, epoch, suite) for suite in suites)
    )


def parse_eval(stage: Stage, epoch: int) -> dict[str, Any]:
    text = stage.eval_report(epoch).read_text(encoding="utf-8", errors="replace")
    pass_rate = re.search(r"pass_rate: `([^`]+)`", text)
    avg_score = re.search(r"avg_score: `([^`]+)`", text)
    return {
        "stage": stage.label,
        "epoch": epoch,
        "checkpoint": rel(stage.checkpoint(epoch)),
        "pass_rate": pass_rate.group(1) if pass_rate else None,
        "avg_score": float(avg_score.group(1)) if avg_score else None,
    }


def summarize(stage: Stage, epoch: int) -> None:
    if summary_exists(stage, epoch):
        return
    item = parse_eval(stage, epoch)
    with SUMMARY.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, sort_keys=True) + "\n")
    log(f"summary {stage.label} e{epoch}: pass_rate={item['pass_rate']} avg={item['avg_score']}")


def summarize_suite(stage: Stage, epoch: int, suite: EvalSuite) -> None:
    if suite_summary_exists(stage, epoch, suite):
        return
    report = stage.suite_eval_report(epoch, suite.name)
    text = report.read_text(encoding="utf-8", errors="replace")
    pass_rate = re.search(r"pass_rate: `([^`]+)`", text)
    avg_score = re.search(r"avg_score: `([^`]+)`", text)
    item = {
        "stage": stage.label,
        "epoch": epoch,
        "checkpoint": rel(stage.checkpoint(epoch)),
        "suite": suite.name,
        "pass_rate": pass_rate.group(1) if pass_rate else None,
        "avg_score": float(avg_score.group(1)) if avg_score else None,
    }
    with SUMMARY.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, sort_keys=True) + "\n")
    log(f"summary {stage.label} e{epoch} {suite.name}: pass_rate={item['pass_rate']} avg={item['avg_score']}")


def run_manual_gate(stage: Stage, epoch: int, probes: list[str], poll_seconds: int) -> None:
    output = stage.manual_report(epoch)
    if output.exists():
        return
    wait_for_vram(2500, poll_seconds, "manual gate")
    checkpoint = rel(stage.checkpoint(epoch))
    code = f"""
from inference import BDHInference
probes = {probes!r}
checkpoint = {checkpoint!r}
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


def run_eval(stage: Stage, epoch: int, probes: list[str], suites: list[EvalSuite], poll_seconds: int) -> bool:
    if not stage.checkpoint(epoch).exists():
        return False
    if not eval_exists(stage, epoch):
        wait_for_vram(2500, poll_seconds, "eval")
        log(f"eval {stage.label} e{epoch}: {rel(stage.checkpoint(epoch))}")
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = "0"
        code = run(
            [
                str(PYTHON),
                "-u",
                "meta/scripts/eval_grounding.py",
                "--checkpoint",
                rel(stage.checkpoint(epoch)),
                "--name",
                f"{stage.prefix}_e{epoch}",
            ],
            env=env,
            stdout=REPORT_DIR / f"{stage.prefix}_e{epoch}_eval.log",
        )
        if code != 0:
            log(f"eval failed for {stage.label} e{epoch}: code {code}")
            return False
    run_manual_gate(stage, epoch, probes, poll_seconds)
    summarize(stage, epoch)
    for suite in suites:
        if stage.suite_eval_report(epoch, suite.name).exists():
            summarize_suite(stage, epoch, suite)
            continue
        wait_for_vram(2500, poll_seconds, f"eval suite {suite.name}")
        log(f"eval {stage.label} e{epoch} suite={suite.name}: {rel(stage.checkpoint(epoch))}")
        cmd = [
            str(PYTHON),
            "-u",
            "meta/scripts/eval_grounding.py",
            "--checkpoint",
            rel(stage.checkpoint(epoch)),
            "--name",
            f"{stage.prefix}_e{epoch}_{suite.name}",
        ]
        if suite.tests is not None:
            cmd.extend(["--tests", rel(suite.tests)])
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = "0"
        code = run(cmd, env=env, stdout=REPORT_DIR / f"{stage.prefix}_e{epoch}_{suite.name}_eval.log")
        if code != 0:
            log(f"eval suite {suite.name} failed for {stage.label} e{epoch}: code {code}")
            return False
        summarize_suite(stage, epoch, suite)
    return True


def train_once(stage: Stage, epoch: int, profile: TrainProfile) -> bool:
    resume = stage.resume_checkpoint(epoch)
    if not resume.exists():
        log(f"cannot train {stage.label} e{epoch}: missing resume {rel(resume)}")
        return False
    train_log = stage.train_log(epoch)
    log(
        f"train {stage.label} e{epoch}: resume={rel(resume)} "
        f"profile={profile.name} output={rel(stage.checkpoint(epoch))}"
    )
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "0"
    env["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"
    cmd = [
        str(PYTHON),
        "-u",
        "train.py",
        "--phase",
        "0",
        "--jsonl-data",
        rel(stage.corpus),
        "--mask-instruction-loss",
        "--prompt-loss-weight",
        "0.0",
        "--prompt-tail-bytes",
        "96",
        "--block-size",
        "128",
        "--resume",
        rel(resume),
        "--output",
        rel(stage.checkpoint(epoch)),
        "--epochs",
        "1",
        "--amp-bf16",
        "--no-shuffle",
        "--lr",
        str(stage.lr),
        "--log-vram",
        *profile.args(),
    ]
    code = run(cmd, env=env, stdout=train_log)
    if code == 0:
        return True
    log(f"train failed for {stage.label} e{epoch}: code {code}")
    return False


def train_with_adaptive_vram(stage: Stage, epoch: int, poll_seconds: int, allow_wait: bool) -> bool:
    start_index = 0
    while start_index < len(PROFILES):
        while active_training():
            if not allow_wait:
                log("another train process is active; not waiting in once mode")
                return False
            log("another train process is active; waiting")
            time.sleep(poll_seconds)

        profile = choose_profile()
        if profile is None:
            if not allow_wait:
                return False
            time.sleep(poll_seconds)
            continue
        profile_index = PROFILES.index(profile)
        if profile_index < start_index:
            profile = PROFILES[start_index]
            free = gpu_free_mib()
            if free is not None and free < profile.min_free_mib:
                if not allow_wait:
                    log(f"profile {profile.name} needs more VRAM; not waiting in once mode")
                    return False
                log(f"waiting for requested fallback profile {profile.name}")
                time.sleep(poll_seconds)
                continue

        ok = train_once(stage, epoch, profile)
        if ok:
            return True
        if log_has_oom(stage.train_log(epoch)):
            start_index = min(PROFILES.index(profile) + 1, len(PROFILES))
            if start_index < len(PROFILES):
                log(f"OOM detected; retrying with profile {PROFILES[start_index].name}")
                time.sleep(30)
                continue
        return False
    log(f"no smaller VRAM profile left for {stage.label} e{epoch}")
    return False


def stage_work_complete(stage: Stage) -> bool:
    raise RuntimeError("stage_work_complete requires eval suites; use stage_work_complete_with_suites")


def stage_work_complete_with_suites(stage: Stage, suites: list[EvalSuite]) -> bool:
    return all(stage.checkpoint(epoch).exists() and eval_complete(stage, epoch, suites) for epoch in range(1, stage.max_epoch + 1))


def work_once(stages: list[Stage], probes: list[str], suites: list[EvalSuite], poll_seconds: int, allow_wait: bool) -> bool:
    for epoch in range(1, max(stage.max_epoch for stage in stages) + 1):
        for stage in stages:
            if epoch > stage.max_epoch:
                continue
            if stage.checkpoint(epoch).exists():
                if not eval_complete(stage, epoch, suites):
                    run_eval(stage, epoch, probes, suites, poll_seconds)
                continue
            if not train_with_adaptive_vram(stage, epoch, poll_seconds, allow_wait):
                return False
            run_eval(stage, epoch, probes, suites, poll_seconds)
            return False
    return True


def load_config(path: Path | None, max_epoch: int) -> tuple[list[Stage], list[str], list[EvalSuite]]:
    if path is None:
        base = ROOT / "core/kernel_e1_focus_repair.pt"
        return (
            [
                Stage(
                    label="sorted",
                    corpus=ROOT / "training/corpus/kernel_c17_ladder_1200_e1.jsonl",
                    prefix="c17_ladder_1200",
                    base=base,
                    max_epoch=max_epoch,
                    order=0,
                ),
                Stage(
                    label="contrast",
                    corpus=ROOT / "training/corpus/kernel_c17_contrast_angle_1200_e1.jsonl",
                    prefix="c17_contrast_angle_1200",
                    base=base,
                    max_epoch=max_epoch,
                    order=1,
                ),
            ],
            DEFAULT_PROBES,
            [],
        )

    data = json.loads((path if path.is_absolute() else ROOT / path).read_text(encoding="utf-8"))
    probes = [str(item) for item in data.get("probes", DEFAULT_PROBES)]
    suites = [
        EvalSuite(
            name=str(item["name"]),
            tests=(ROOT / str(item["tests"])) if item.get("tests") else None,
        )
        for item in data.get("eval_suites", [])
    ]
    stages: list[Stage] = []
    for idx, item in enumerate(data["stages"]):
        stages.append(
            Stage(
                label=str(item["label"]),
                corpus=ROOT / str(item["corpus"]),
                prefix=str(item["prefix"]),
                base=ROOT / str(item.get("base", "core/kernel_e1_focus_repair.pt")),
                max_epoch=int(item.get("max_epoch", data.get("max_epoch", max_epoch))),
                order=int(item.get("order", idx)),
                lr=float(item.get("lr", data.get("lr", 1e-4))),
            )
        )
    return sorted(stages, key=lambda stage: stage.order), probes, suites


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--max-epoch", type=int, default=4)
    parser.add_argument("--poll-seconds", type=int, default=1800)
    parser.add_argument("--once", action="store_true", help="Run one scheduler action and exit.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    stages, probes, suites = load_config(args.config, args.max_epoch)
    log(
        "campaign runner start: "
        f"stages={','.join(stage.label for stage in stages)}, "
        f"eval_suites={','.join(suite.name for suite in suites) or 'none'}, "
        f"max_epoch={args.max_epoch}, poll_seconds={args.poll_seconds}"
    )
    while True:
        done = work_once(stages, probes, suites, args.poll_seconds, allow_wait=not args.once)
        if done and all(stage_work_complete_with_suites(stage, suites) for stage in stages):
            log("campaign runner complete")
            return
        if args.once:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
