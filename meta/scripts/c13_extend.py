#!/usr/bin/env python3
"""
Campaign 13 extension — runs after c13_orchestrate.py completes.

Strategy:
  After the orchestrator establishes the best phase sequence, take the final
  winner checkpoint and run additional epochs of every phase corpus in order
  (no bridge — bridge consistently hurt between phases in the base run).

  Phases tried:
    - Succeeded in base run (A, C so far): 2 extra epochs each — squeeze more
      learning out of the established curriculum.
    - Failed in base run (B, D, E so far): 5 epochs — more epochs may absorb
      content that 3 epochs couldn't.

  One full pass through all 5 corpora. If any phase improved, queue a second
  pass for the ones that improved. Stop when a full pass produces no improvement.

Results appended to: training/logs/campaign_13_reports/orchestrator_log.md
Per-epoch detail:    training/logs/campaign_13_reports/<run>_e<N>_results.txt
"""

import subprocess, re, sys, time
from pathlib import Path
from datetime import datetime

PYTHON   = "/home/aomukai/.unsloth/studio/unsloth_studio/bin/python"
BASE     = Path(__file__).resolve().parent.parent.parent
LOG_DIR  = BASE / "training/logs/campaign_13_reports"
CORP_DIR = BASE / "training/corpus"
CORE_DIR = BASE / "core"
CKPT_DIR = BASE / "checkpoints"
CAMPAIGN = 13
BATCH    = 4   # throttled; 8 on dedicated GPU day

MASTER_LOG = LOG_DIR / "orchestrator_log.md"


# ── helpers (same as orchestrator) ───────────────────────────────────────────

def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg):
    line = f"[{ts()}] {msg}"
    print(line, flush=True)
    with open(MASTER_LOG, "a") as f:
        f.write(line + "\n")


def section(title):
    bar = "=" * 60
    log(f"\n{bar}\n  {title}\n{bar}")
    with open(MASTER_LOG, "a") as f:
        f.write(f"\n## {title}\n\n")


def run_eval(ckpt):
    r = subprocess.run(
        [PYTHON, "eval.py", "--checkpoint", str(ckpt)],
        capture_output=True, text=True, cwd=BASE, timeout=300,
    )
    out = r.stdout + r.stderr
    def flt(pat, default=0.0):
        m = re.search(pat, out)
        return float(m.group(1)) if m else default
    shaped = flt(r"SHAPED avg:\s+([0-9.]+)")
    raw    = flt(r"RAW avg:\s+([0-9.]+)")
    m = re.search(r"loop\s+(\d+)x", out)
    loops  = int(m.group(1)) if m else 0
    return shaped, raw, loops, out


def run_probe(ckpt):
    r = subprocess.run(
        [PYTHON, "meta/scripts/probe.py",
         "--checkpoint", str(ckpt), "--temperature", "0.7", "--tokens", "120"],
        capture_output=True, text=True, cwd=BASE, timeout=300,
    )
    return r.stdout


def train_epochs(name, corpus, resume, epochs, batch=BATCH):
    output    = CORE_DIR / f"{name}.pt"
    train_log = LOG_DIR  / f"{name}_train.log"

    epoch_ckpts = [CORE_DIR / f"{name}_e{ep}.pt" for ep in range(1, epochs + 1)]
    if all(p.exists() for p in epoch_ckpts):
        log(f"  '{name}': all checkpoints exist — skipping training, re-running eval")
        content = train_log.read_text() if train_log.exists() else ""
    else:
        for attempt_batch in [batch, batch // 2]:
            cmd = [
                PYTHON, "train.py",
                "--phase", "0",
                "--corpus-file", str(corpus),
                "--output", str(output),
                "--epochs", str(epochs),
                "--epoch-checkpoints",
                "--batch-size", str(attempt_batch),
                "--amp-bf16",
                "--resume", str(resume),
            ]
            log(f"  train '{name}' ({epochs} ep, batch={attempt_batch}, "
                f"resume={Path(resume).name})")
            with open(train_log, "w") as f:
                proc = subprocess.Popen(cmd, stdout=f, stderr=f, cwd=BASE)
                proc.wait()
            with open(train_log) as f:
                content = f.read()
            if "OutOfMemoryError" in content or "out of memory" in content.lower():
                log(f"  OOM at batch={attempt_batch}; retrying batch={attempt_batch // 2}")
                continue
            break

    losses = {int(m.group(1)): float(m.group(2))
              for m in re.finditer(r"epoch\s+(\d+)/\d+\s+loss\s+([0-9.]+)", content)}

    history = {}
    best_shaped, best_epoch, best_ckpt = -1.0, 0, None

    for ep in range(1, epochs + 1):
        ckpt = CORE_DIR / f"{name}_e{ep}.pt"
        if not ckpt.exists():
            log(f"  WARNING: {ckpt.name} missing")
            break
        shaped, raw, loops, eval_out = run_eval(ckpt)
        probe_out = run_probe(ckpt)
        loss = losses.get(ep)

        result_path = LOG_DIR / f"{name}_e{ep}_results.txt"
        with open(result_path, "w") as f:
            f.write(f"# {name} — Epoch {ep}\n")
            f.write(f"Loss: {loss}  Raw: {raw:.3f}  Shaped: {shaped:.3f}  Loops: {loops}\n\n")
            f.write("=== EVAL ===\n"); f.write(eval_out)
            f.write("\n=== PROBE ===\n"); f.write(probe_out)

        history[ep] = {"loss": loss, "shaped": shaped, "raw": raw,
                       "loops": loops, "ckpt": str(ckpt)}
        log(f"  E{ep}: loss={loss}  raw={raw:.3f}  shaped={shaped:.3f}  loops={loops}")

        if shaped > best_shaped:
            best_shaped, best_epoch, best_ckpt = shaped, ep, ckpt

    log(f"  best: E{best_epoch} shaped={best_shaped:.3f}")
    return history, best_ckpt, best_shaped, best_epoch


def promote(ckpt, label):
    dest = CKPT_DIR / f"{label}.pt"
    subprocess.run(["cp", str(ckpt), str(dest)], check=True)
    log(f"  promoted → checkpoints/{label}.pt")
    return dest


def wait_for_orchestrator():
    """Block until orchestrator PID exits or 'Completed' appears in master log."""
    log("Waiting for orchestrator to complete ...")
    while True:
        try:
            with open(MASTER_LOG) as f:
                content = f.read()
            if "Completed:" in content:
                log("Orchestrator complete — starting extension.")
                return
        except FileNotFoundError:
            pass
        time.sleep(60)


def parse_orchestrator_final(log_content):
    """
    Extract the final checkpoint path and shaped score from orchestrator log.
    Falls back to scanning promoted checkpoints.
    """
    m = re.search(r"Final checkpoint.*?`([^`]+)`.*?shaped=([0-9.]+)", log_content)
    if m:
        name   = m.group(1)           # e.g. c13_Phase_C_winner.pt
        shaped = float(m.group(2))
        # Try checkpoints/ first, then core/
        for dir_ in [CKPT_DIR, CORE_DIR]:
            p = dir_ / name
            if p.exists():
                return p, shaped
    # fallback: find the most recently promoted winner
    winners = sorted(CKPT_DIR.glob("c13_*_winner.pt"), key=lambda p: p.stat().st_mtime)
    if winners:
        log(f"  fallback: using most recent winner {winners[-1].name}")
        return winners[-1], None
    return None, None


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    wait_for_orchestrator()

    with open(MASTER_LOG) as f:
        orch_content = f.read()

    final_ckpt, final_shaped = parse_orchestrator_final(orch_content)
    if final_ckpt is None:
        log("ERROR: could not determine final checkpoint from orchestrator log.")
        sys.exit(1)

    if final_shaped is None:
        # run eval to get shaped score
        shaped, raw, loops, _ = run_eval(final_ckpt)
        final_shaped = shaped
        log(f"Final checkpoint eval: shaped={final_shaped:.3f}")

    with open(MASTER_LOG, "a") as f:
        f.write(f"\n---\n\n# Extension Pass\n\nStarted: {ts()}\n\n")
        f.write(f"Base checkpoint: `{final_ckpt.name}`  shaped={final_shaped:.3f}\n\n")
        f.write("No bridge between phases (bridge consistently hurt in base run).\n\n")

    # Phase specs: (label, corpus_key, extra_epochs)
    # Succeeded phases get 2 extra epochs; previously-failed get 5.
    phase_specs = [
        ("Phase_A_ext",  "phase_A",  2),   # succeeded — squeeze more
        ("Phase_B_ext",  "phase_B",  5),   # failed — more epochs
        ("Phase_C_ext",  "phase_C",  2),   # succeeded — squeeze more
        ("Phase_D_ext",  "phase_D",  5),   # failed — more epochs
        ("Phase_E_ext",  "phase_E",  5),   # failed — more epochs
    ]

    prev_ckpt   = final_ckpt
    prev_shaped = final_shaped
    pass_num    = 1

    while True:
        section(f"Extension pass {pass_num}")
        improved_any = False

        for label, corpus_key, epochs in phase_specs:
            corpus = CORP_DIR / f"campaign_{CAMPAIGN}_{corpus_key}.txt"
            if not corpus.exists():
                log(f"  {label}: corpus missing, skipping")
                continue

            run_name = f"c13_{label}_p{pass_num}"
            section(f"{label} ({epochs} ep, pass {pass_num})")
            _, best_ckpt, best_shaped, best_epoch = train_epochs(
                run_name, corpus, resume=prev_ckpt, epochs=epochs)

            delta = best_shaped - prev_shaped
            with open(MASTER_LOG, "a") as f:
                status = "IMPROVED" if best_shaped > prev_shaped else "no improvement"
                f.write(f"| {label} | E{best_epoch} | {best_shaped:.3f} "
                        f"| {delta:+.3f} | {status} |\n")

            if best_shaped > prev_shaped:
                promote(best_ckpt, f"c13_{label}_p{pass_num}_winner")
                prev_ckpt   = best_ckpt
                prev_shaped = best_shaped
                improved_any = True
                log(f"  IMPROVED: {label} → shaped={prev_shaped:.3f}")
            else:
                log(f"  No improvement: {label} (best={best_shaped:.3f} vs {prev_shaped:.3f})")

        if not improved_any:
            log(f"Pass {pass_num}: no phase improved. Extension complete.")
            break

        pass_num += 1
        if pass_num > 4:   # hard ceiling — avoid infinite training
            log("Reached maximum 4 extension passes. Stopping.")
            break

    section("Extension complete")
    with open(MASTER_LOG, "a") as f:
        f.write(f"\n### Extension final result\n\n"
                f"Checkpoint: `{prev_ckpt.name}`  shaped={prev_shaped:.3f}\n\n"
                f"Completed: {ts()}\n")
    log(f"Done. Final: {prev_ckpt.name} shaped={prev_shaped:.3f}")


if __name__ == "__main__":
    main()
