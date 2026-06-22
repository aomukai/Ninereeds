#!/usr/bin/env python3
"""
C15 automated pipeline: for each block, wait for training → eval all epochs →
brain_map all epochs → pick winner → promote → launch next block.

Winner selection: highest arithmetic_jp after-hub (thinking scan).
Tiebreaker: shaped score from eval.py.

Usage:
    python3 meta/scripts/c15_pipeline.py --start-block 2
    python3 meta/scripts/c15_pipeline.py --start-block 3 --base checkpoints/c15_arith_grounded_winner.pt
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PYTHON = "/home/aomukai/.unsloth/studio/unsloth_studio/bin/python"
LOGS = ROOT / "training/logs/campaign_15_reports"
BRAIN_LOGS = ROOT / "training/logs/brain_maps"
CHECKPOINTS = ROOT / "checkpoints"
CORE = ROOT / "core"

BLOCKS = {
    2: {
        "name": "c15_arith_grounded",
        "corpus": "training/corpus/c15_arith_grounded.txt",
        "output": CORE / "c15_arith_grounded.pt",
        "winner": CHECKPOINTS / "c15_arith_grounded_winner.pt",
        "train_log": LOGS / "c15_arith_grounded_train.log",
        "eval_log": LOGS / "c15_arith_grounded_eval.log",
    },
    3: {
        "name": "c15_reasoning",
        "corpus": "training/corpus/c15_reasoning_arithB.txt",
        "output": CORE / "c15_reasoning.pt",
        "winner": CHECKPOINTS / "c15_reasoning_winner.pt",
        "train_log": LOGS / "c15_reasoning_train.log",
        "eval_log": LOGS / "c15_reasoning_eval.log",
    },
    4: {
        "name": "c15_vignettes",
        "corpus": "training/corpus/c15_vignettes.txt",
        "output": CORE / "c15_vignettes.pt",
        "winner": CHECKPOINTS / "c15_vignettes_winner.pt",
        "train_log": LOGS / "c15_vignettes_train.log",
        "eval_log": LOGS / "c15_vignettes_eval.log",
    },
    5: {
        "name": "c15_education",
        "corpus": "training/corpus/c15_education.txt",
        "output": CORE / "c15_education.pt",
        "winner": CHECKPOINTS / "c15_education_winner.pt",
        "train_log": LOGS / "c15_education_train.log",
        "eval_log": LOGS / "c15_education_eval.log",
    },
}

EPOCHS = 3


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)


def epoch_ckpt(block_name: str, e: int) -> Path:
    return CORE / f"{block_name}_e{e}.pt"


def wait_for_training(block: dict, poll=60):
    """Wait until all 3 epoch checkpoints exist."""
    name = block["name"]
    needed = [epoch_ckpt(name, e) for e in range(1, EPOCHS + 1)]
    missing = [p for p in needed if not p.exists()]
    if not missing:
        log(f"  All epoch checkpoints already present for {name}.")
        return
    log(f"  Waiting for training to finish: {name}")
    while True:
        missing = [p for p in needed if not p.exists()]
        if not missing:
            log(f"  Training complete: {name}")
            return
        log(f"  Still waiting — missing: {[p.name for p in missing]}")
        time.sleep(poll)


def run_eval(checkpoint: Path) -> float:
    """Run eval.py, return shaped score. Returns 0.0 on failure."""
    result = subprocess.run(
        [PYTHON, str(ROOT / "eval.py"), "--checkpoint", str(checkpoint)],
        capture_output=True, text=True, cwd=ROOT,
        env={**os.environ, "CUDA_VISIBLE_DEVICES": "0"},
    )
    output = result.stdout + result.stderr
    for line in output.splitlines():
        if "SHAPED avg:" in line:
            try:
                return float(line.split(":")[1].strip().split()[0])
            except Exception:
                pass
    log(f"  WARNING: could not parse shaped score from eval for {checkpoint.name}")
    return 0.0


def run_brain_map(checkpoint: Path, probes_file: str, scan_name: str):
    subprocess.run(
        [PYTHON, str(ROOT / "meta/scripts/brain_map.py"), "probe",
         "--checkpoint", str(checkpoint),
         "--probes", probes_file,
         "--name", scan_name],
        cwd=ROOT, check=True,
    )
    subprocess.run(
        [PYTHON, str(ROOT / "meta/scripts/brain_map.py"), "hubs",
         "--name", scan_name, "--threshold", "0.7"],
        cwd=ROOT, check=True,
    )


def get_after_hub(scan_name: str, category: str) -> float:
    hub_file = BRAIN_LOGS / f"{scan_name}_hubs.json"
    if not hub_file.exists():
        return 0.0
    try:
        data = json.loads(hub_file.read_text())
        return data.get("similarity_after", {}).get(category, 0.0)
    except Exception:
        return 0.0


def get_shaped(scan_name: str) -> float:
    """Read shaped score from brain_map eval log section (fallback)."""
    return 0.0  # filled by eval_and_scan


def eval_and_scan(block: dict) -> dict:
    """Run eval + brain scans on all 3 epochs. Return dict of results."""
    name = block["name"]
    results = {}
    eval_log = block["eval_log"]

    with open(eval_log, "w") as flog:
        for e in range(1, EPOCHS + 1):
            ckpt = epoch_ckpt(name, e)
            log(f"  Eval E{e}: {ckpt.name}")
            flog.write(f"\n========== {name.upper()} E{e} ==========\n")
            flog.flush()

            shaped = run_eval(ckpt)
            flog.write(f"shaped: {shaped:.4f}\n")
            flog.flush()

            lang_name = f"{name}_e{e}_language"
            think_name = f"{name}_e{e}_thinking"

            log(f"  Brain map language E{e}...")
            run_brain_map(ckpt, "training/corpus_admin/probe_sets/language.jsonl", lang_name)

            log(f"  Brain map thinking E{e}...")
            run_brain_map(ckpt, "training/corpus_admin/probe_sets/thinking.jsonl", think_name)

            arith_jp = get_after_hub(think_name, "arithmetic_jp")
            arith_zh = get_after_hub(think_name, "arithmetic_zh")
            spatial   = get_after_hub(f"{name}_e{e}_language", "spatial")

            flog.write(f"arithmetic_jp after-hub: {arith_jp:.4f}\n")
            flog.write(f"arithmetic_zh after-hub: {arith_zh:.4f}\n")
            flog.write(f"spatial after-hub: {spatial:.4f}\n")
            flog.flush()

            results[e] = {
                "shaped": shaped,
                "arithmetic_jp": arith_jp,
                "arithmetic_zh": arith_zh,
                "spatial": spatial,
            }
            log(f"  E{e}: shaped={shaped:.4f} arith_jp={arith_jp:.4f} spatial={spatial:.4f}")

    return results


def pick_winner(results: dict) -> int:
    """Pick best epoch: highest arithmetic_jp, tiebreak by shaped."""
    ranked = sorted(results.items(), key=lambda kv: (kv[1]["arithmetic_jp"], kv[1]["shaped"]), reverse=True)
    best_e, best = ranked[0]
    log(f"  Winner: E{best_e} (arith_jp={best['arithmetic_jp']:.4f}, shaped={best['shaped']:.4f})")
    for e, r in ranked:
        marker = " <-- WINNER" if e == best_e else ""
        log(f"    E{e}: shaped={r['shaped']:.4f} arith_jp={r['arithmetic_jp']:.4f} spatial={r['spatial']:.4f}{marker}")
    return best_e


def wait_for_gpu_memory(min_free_mib: int = 1300, poll: int = 30):
    """Wait until GPU 0 has at least min_free_mib MiB free and memory is stable.
    Purpose: ensure the eval process has fully released CUDA memory before training launches.
    Not designed to wait for mnm.exe — that's a separate concern."""
    import subprocess as sp
    log("  Waiting 30s for CUDA memory to settle after eval...")
    time.sleep(30)
    while True:
        result = sp.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True,
        )
        lines = result.stdout.strip().splitlines()
        free = int(lines[0].strip()) if lines else 0
        log(f"  GPU 0 free: {free} MiB (need {min_free_mib})")
        if free >= min_free_mib:
            return
        log(f"  Not enough free memory — waiting...")
        time.sleep(poll)


def launch_training(block: dict, base: Path):
    name = block["name"]
    log(f"  Checking GPU memory before training: {name}")
    wait_for_gpu_memory()
    log(f"  Launching training: {name} from {base.name}")
    cmd = [
        "env", "CUDA_VISIBLE_DEVICES=0",
        f"PYTORCH_ALLOC_CONF=expandable_segments:True",
        "nohup", PYTHON, str(ROOT / "train.py"),
        "--phase", "0",
        "--corpus-file", block["corpus"],
        "--output", str(block["output"]),
        "--resume", str(base),
        "--epochs", str(EPOCHS),
        "--epoch-checkpoints",
        "--amp-bf16",
        "--no-shuffle",
        "--batch-size", "1",
        "--grad-accum-steps", "2",
        "--adam8bit",
    ]
    log_path = block["train_log"]
    with open(log_path, "w") as flog:
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=flog, stderr=flog)
    log(f"  Training PID: {proc.pid} → {log_path.name}")


def run_block(block_num: int, base: Path, skip_training: bool = False):
    block = BLOCKS[block_num]
    name = block["name"]
    log(f"\n{'='*60}")
    log(f"BLOCK {block_num}: {name}")
    log(f"{'='*60}")

    if not skip_training:
        all_done = all(epoch_ckpt(name, e).exists() for e in range(1, EPOCHS + 1))
        if all_done:
            log("  Epoch checkpoints found — skipping training.")
        else:
            launch_training(block, base)
            wait_for_training(block)
    else:
        wait_for_training(block)

    results = eval_and_scan(block)
    best_e = pick_winner(results)

    winner_ckpt = epoch_ckpt(name, best_e)
    dest = block["winner"]
    shutil.copy2(winner_ckpt, dest)
    log(f"  Promoted: {winner_ckpt.name} → {dest.name}")

    return dest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-block", type=int, default=2,
                        help="Block number to start from (2–5)")
    parser.add_argument("--base", type=Path, default=None,
                        help="Base checkpoint for the start block (if not auto-derived)")
    args = parser.parse_args()

    start = args.start_block
    base = args.base

    if base is None:
        if start == 2:
            base = CHECKPOINTS / "c15_language_winner.pt"
        else:
            base = BLOCKS[start - 1]["winner"]

    if not base.exists():
        log(f"ERROR: base checkpoint not found: {base}")
        sys.exit(1)

    log(f"C15 pipeline starting at Block {start}, base: {base.name}")

    winner = base
    for block_num in range(start, 6):
        skip_train = (block_num == start and
                      all(epoch_ckpt(BLOCKS[block_num]["name"], e).exists()
                          for e in range(1, EPOCHS + 1)))
        winner = run_block(block_num, winner, skip_training=skip_train)

    log("\nC15 PIPELINE COMPLETE")
    log(f"Final winner: {winner}")


if __name__ == "__main__":
    main()
