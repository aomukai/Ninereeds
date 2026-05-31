#!/usr/bin/env python3
"""
Campaign 13 overnight orchestrator.

Experiment tree:
  1. Phase A-only winner (E3=0.914, confirmed by E5 eval at startup)
  2. Fresh → Bridge(1ep) → Phase A(3ep) → compare vs #1 → pick Phase A winner
  3. Phase A winner → Phase B direct(3ep)  vs  Bridge(1ep)→Phase B(3ep) → compare
  4. Phase B winner → Phase C → same pattern
  5. Phase C winner → Phase D → same
  6. Phase D winner → Phase E → same

Regression handling:
  If best variant for a phase scores below the incoming baseline (prev_shaped),
  the phase is deferred: pushed to the end of the queue and retried later.
  When a deferred phase fails as the last item in the queue it is marked
  permanently failed and skipped.

All results logged to: training/logs/campaign_13_reports/orchestrator_log.md
Per-epoch eval+probe:  training/logs/campaign_13_reports/<run>_e<N>_results.txt
"""

import subprocess, re, sys, time
from pathlib import Path
from datetime import datetime

PYTHON   = "/home/aomukai/.unsloth/studio/unsloth_studio/bin/python"
BASE     = Path(__file__).resolve().parent.parent.parent
LOG_DIR  = BASE / "training/logs/campaign_13_reports"
CORP_DIR = BASE / "training/corpus"
ORD_DIR  = BASE / "training/training_order"
CORE_DIR = BASE / "core"
CKPT_DIR = BASE / "checkpoints"
CAMPAIGN = 13
BATCH    = 4   # throttled; 8 on dedicated GPU day

MASTER_LOG = LOG_DIR / "orchestrator_log.md"


# ── helpers ──────────────────────────────────────────────────────────────────

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
    """Returns (shaped, raw, loops, full_output)."""
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


def build_corpus(phase):
    corpus = CORP_DIR / f"campaign_{CAMPAIGN}_{phase}.txt"
    report = CORP_DIR / f"campaign_{CAMPAIGN}_{phase}_report.txt"
    order  = ORD_DIR  / f"{phase}_order.jsonl"
    if corpus.exists():
        log(f"  corpus exists: {corpus.name}")
        return corpus
    log(f"  building corpus: {phase} ...")
    r = subprocess.run(
        [PYTHON, "meta/scripts/build_training_corpus.py",
         "--order-file", str(order), "--output", str(corpus), "--report", str(report)],
        capture_output=True, text=True, cwd=BASE, timeout=600,
    )
    ok = r.returncode == 0
    log(f"  corpus {'OK' if ok else 'FAILED'}" + (f": {r.stderr[:300]}" if not ok else ""))
    return corpus if ok else None


def wait_for(path, poll=30):
    path = Path(path)
    while not path.exists():
        time.sleep(poll)


def train_epochs(name, corpus, resume=None, epochs=3, batch=BATCH):
    """
    Train `epochs` epochs with --epoch-checkpoints.
    Skips training if all epoch checkpoints already exist (resume after restart).
    Auto-retries with batch//2 on OOM.
    Returns (history, best_ckpt, best_shaped, best_epoch).
    history = {epoch: {loss, shaped, raw, loops, ckpt}}
    """
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
            ]
            if resume:
                cmd += ["--resume", str(resume)]

            log(f"  train '{name}' ({epochs} ep, batch={attempt_batch}, "
                f"resume={Path(resume).name if resume else 'fresh'})")

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
            log(f"  WARNING: {ckpt.name} missing — training ended early")
            break

        log(f"  eval e{ep} ...")
        shaped, raw, loops, eval_out = run_eval(ckpt)
        log(f"  probe e{ep} ...")
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


def write_comparison(title, variants, prev_shaped):
    """
    variants = list of {label, shaped, epoch, ckpt}.
    Returns (winner_dict, regressed: bool).
    regressed=True when winner shaped < prev_shaped.
    """
    winner = max(variants, key=lambda v: v["shaped"])
    regressed = winner["shaped"] < prev_shaped
    with open(MASTER_LOG, "a") as f:
        f.write(f"| Variant | Best epoch | Shaped | Δ vs baseline | |\n")
        f.write(f"|---|---|---|---|---|\n")
        for v in variants:
            delta = v["shaped"] - prev_shaped
            mark  = "✓ winner" if v is winner else ""
            f.write(f"| {v['label']} | E{v['epoch']} | {v['shaped']:.3f} "
                    f"| {delta:+.3f} | {mark} |\n")
        if regressed:
            f.write(f"\n**REGRESSION** — best {winner['shaped']:.3f} < baseline "
                    f"{prev_shaped:.3f}. Phase deferred.\n\n")
        else:
            f.write(f"\n**Winner:** {winner['label']}  shaped={winner['shaped']:.3f}  "
                    f"Δ={winner['shaped']-prev_shaped:+.3f}  "
                    f"`{Path(winner['ckpt']).name}`\n\n")
    return winner, regressed


def run_phase(phase_label, corpus, br_corpus, prev_ckpt, prev_shaped, attempt):
    """
    Train both variants (direct + bridge-pre) for one phase.
    Returns (winner_dict, regressed: bool).
    """
    safe   = phase_label.replace(" ", "_")
    suffix = f"_retry{attempt}" if attempt > 1 else ""

    section(f"{phase_label} attempt {attempt} — direct (3ep)")
    _, dir_ckpt, dir_shaped, dir_epoch = train_epochs(
        f"c13_{safe}_direct{suffix}", corpus, resume=prev_ckpt, epochs=3)

    section(f"{phase_label} attempt {attempt} — bridge-pre (1ep bridge + 3ep phase)")
    _, bpre_ckpt, _, _ = train_epochs(
        f"c13_{safe}_bridge_pre{suffix}", br_corpus, resume=prev_ckpt, epochs=1)
    _, bph_ckpt, bph_shaped, bph_epoch = train_epochs(
        f"c13_{safe}_bridged{suffix}", corpus, resume=bpre_ckpt, epochs=3)

    section(f"{phase_label} attempt {attempt} — comparison")
    variants = [
        {"label": "Direct",        "shaped": dir_shaped,
         "epoch": dir_epoch,  "ckpt": str(dir_ckpt)},
        {"label": "Bridge+Direct", "shaped": bph_shaped,
         "epoch": bph_epoch,  "ckpt": str(bph_ckpt)},
    ]
    return write_comparison(phase_label, variants, prev_shaped)


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    with open(MASTER_LOG, "w") as f:
        f.write(f"# Campaign 13 Orchestrator Log\n\nStarted: {ts()}\n\n")
        f.write("## Design\n\n")
        f.write("Bridge vs no-bridge comparison for Phase A through E.\n")
        f.write("Regression: phase is deferred (pushed to end of queue).\n")
        f.write("Permanent failure: phase regresses when tried last in queue.\n\n")

    # ── 1. Wait for E5; determine Phase A-only winner ─────────────────────────
    section("Phase A-only: evaluating E5 and picking winner")

    e5_ckpt = CORE_DIR / "campaign_13_phase_A_e5.pt"
    log("Waiting for E5 checkpoint ...")
    wait_for(e5_ckpt)
    log("E5 found; eval + probe ...")

    shaped_e5, raw_e5, loops_e5, eval_e5 = run_eval(e5_ckpt)
    probe_e5 = run_probe(e5_ckpt)

    with open(LOG_DIR / "campaign_13_phase_A_e5_results.txt", "w") as f:
        f.write(f"# Phase A E5\nShaped: {shaped_e5:.3f}  Raw: {raw_e5:.3f}  "
                f"Loops: {loops_e5}\n\n=== EVAL ===\n")
        f.write(eval_e5)
        f.write("\n=== PROBE ===\n")
        f.write(probe_e5)

    log(f"E5: raw={raw_e5:.3f}  shaped={shaped_e5:.3f}  loops={loops_e5}")

    # E1–E4 scores from the live session
    known = {1: 0.906, 2: 0.903, 3: 0.914, 4: 0.907, 5: shaped_e5}
    pa_winner_epoch  = max(known, key=known.get)
    pa_winner_shaped = known[pa_winner_epoch]
    pa_winner_ckpt   = CORE_DIR / f"campaign_13_phase_A_e{pa_winner_epoch}.pt"
    log(f"Phase A-only winner: E{pa_winner_epoch} (shaped={pa_winner_shaped:.3f})")

    with open(MASTER_LOG, "a") as f:
        f.write("### Phase A-only epoch scores\n\n| Epoch | Shaped |\n|---|---|\n")
        for ep, sc in sorted(known.items()):
            mark = " ← winner" if ep == pa_winner_epoch else ""
            f.write(f"| E{ep} | {sc:.3f}{mark} |\n")
        f.write("\n")

    # ── 2. Build all needed corpora ───────────────────────────────────────────
    section("Building corpora")
    pa_corpus = CORP_DIR / f"campaign_{CAMPAIGN}_phase_A.txt"
    br_corpus = build_corpus("bridge")
    pb_corpus = build_corpus("phase_B")
    pc_corpus = build_corpus("phase_C")
    pd_corpus = build_corpus("phase_D")
    pe_corpus = build_corpus("phase_E")

    if not all([br_corpus, pb_corpus, pc_corpus, pd_corpus, pe_corpus]):
        log("ERROR: corpus build failed — aborting.")
        sys.exit(1)

    # ── 3. Fresh → Bridge(1ep) → Phase A(3ep) ────────────────────────────────
    section("Fresh → Bridge(1ep) → Phase A(3ep)")

    _, br_ckpt, br_shaped, _ = train_epochs(
        "c13_fresh_bridge", br_corpus, resume=None, epochs=1)
    log(f"Bridge base shaped={br_shaped:.3f}")

    _, brA_ckpt, brA_shaped, brA_epoch = train_epochs(
        "c13_fresh_bridge_phaseA", pa_corpus, resume=br_ckpt, epochs=3)

    # ── 4. Phase A final comparison ───────────────────────────────────────────
    section("Phase A final comparison")
    # Both variants start from fresh so prev_shaped=0 (no regression possible here,
    # we simply pick the higher score).
    pa_variants = [
        {"label": "Phase A-only",   "shaped": pa_winner_shaped,
         "epoch": pa_winner_epoch,  "ckpt": str(pa_winner_ckpt)},
        {"label": "Bridge+Phase A", "shaped": brA_shaped,
         "epoch": brA_epoch,        "ckpt": str(brA_ckpt)},
    ]
    pa_overall, _ = write_comparison("Phase A", pa_variants, prev_shaped=0.0)
    promote(Path(pa_overall["ckpt"]), "c13_phaseA_winner")
    prev_ckpt   = Path(pa_overall["ckpt"])
    prev_shaped = pa_overall["shaped"]
    log(f"Phase A overall winner: {pa_overall['label']} shaped={prev_shaped:.3f}")

    # ── 5–8. Phases B → E with regression deferral ───────────────────────────
    #
    # queue entries: (phase_label, corpus, attempt_number)
    # On regression + more phases remain: push to end of queue (attempt += 1).
    # On regression + last in queue: permanent failure.
    #
    MAX_ATTEMPTS = 4  # permanent fail after this many attempts regardless of queue state

    queue = [
        ("Phase B", pb_corpus, 1),
        ("Phase C", pc_corpus, 1),
        ("Phase D", pd_corpus, 1),
        ("Phase E", pe_corpus, 1),
    ]
    succeeded = []   # [(label, shaped)]
    failed    = []   # [label]

    while queue:
        phase_label, corpus, attempt = queue.pop(0)
        is_last = (len(queue) == 0) or (attempt >= MAX_ATTEMPTS)

        winner, regressed = run_phase(
            phase_label, corpus, br_corpus, prev_ckpt, prev_shaped, attempt)

        if regressed:
            if is_last:
                log(f"PERMANENT FAILURE: {phase_label} after {attempt} attempts.")
                failed.append(phase_label)
            else:
                log(f"DEFERRED: {phase_label} (attempt {attempt}) → end of queue.")
                queue.append((phase_label, corpus, attempt + 1))
        else:
            safe = phase_label.replace(" ", "_")
            promote(Path(winner["ckpt"]), f"c13_{safe}_winner")
            prev_ckpt   = Path(winner["ckpt"])
            prev_shaped = winner["shaped"]
            succeeded.append((phase_label, winner["shaped"]))
            log(f"SUCCESS: {phase_label} — new baseline shaped={prev_shaped:.3f}")

    # ── Final summary ─────────────────────────────────────────────────────────
    section("Final summary")
    with open(MASTER_LOG, "a") as f:
        f.write("### Succeeded\n\n")
        for label, sc in succeeded:
            f.write(f"- {label}: shaped={sc:.3f}\n")
        f.write("\n### Permanently failed (regression in all queue positions)\n\n")
        for label in (failed if failed else ["(none)"]):
            f.write(f"- {label}\n")
        f.write(f"\n### Final checkpoint\n\n"
                f"`{prev_ckpt.name}` shaped={prev_shaped:.3f}\n\n"
                f"Completed: {ts()}\n")

    log(f"Done. Master log: {MASTER_LOG}")
    log(f"Per-epoch detail: {LOG_DIR}/<run>_e<N>_results.txt")


if __name__ == "__main__":
    main()
