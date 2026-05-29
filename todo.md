# TODO

Active work queue. See `training/docs/training.md` for the full procedure.
Completed phases: `archive/milestones/2026-05-29_corpus_milestone.md`.

---

## Nomenclature

**Campaign** = one experimental run covering one or more training phases.
A campaign ends when all planned phases complete or a regression warrants stopping.
Reports live in `training/logs/campaign_N_reports/`, named `NN_phase_X.md`.

---

## Campaign 13 — Dependency-ordered curriculum, 25M crash test

**Goal:** Validate the new Phase A–E curriculum ordering on 25M before scaling.
Train one phase at a time, probe after each, decide whether to continue.
25M is the crash-test model — if ordering is wrong it shows cheaply here.

**Model:** `--scale-25m`
**Base checkpoint:** fresh start (no prior checkpoint)
**Corpus:** `training/training_order/phase_X_order.jsonl` per phase

### Immediate next steps

- [ ] Build Phase A corpus:
  ```bash
  python meta/scripts/build_training_corpus.py \
    --order-file training/training_order/phase_A_order.jsonl \
    --output training/corpus/campaign_13_phase_A.txt \
    --report training/corpus/campaign_13_phase_A_report.txt
  ```
- [ ] Train Phase A (25M, 3 epochs, GPU 0):
  ```bash
  CUDA_VISIBLE_DEVICES=0 nohup python train.py \
    --phase 0 \
    --corpus-file training/corpus/campaign_13_phase_A.txt \
    --output core/campaign_13_phase_A.pt \
    --scale-25m --epochs 3 --epoch-checkpoints --amp-bf16 \
    > training/logs/campaign_13_reports/phase_A_train.log 2>&1 &
  ```
- [ ] Probe + eval each epoch → fill `training/logs/campaign_13_reports/01_phase_A.md`
- [ ] Decide: continue to Phase B, or adjust ordering first

### Phase sequence (planned, subject to revision after each eval)

| Step | Corpus | Report |
|------|--------|--------|
| 1 | Phase A — concrete anchors | `01_phase_A.md` |
| 2 | Bridge (grammar reset) | `02_bridge.md` |
| 3 | Phase B — concrete relations | `03_phase_B.md` |
| 4 | Bridge | `04_bridge.md` |
| 5 | Phase C — agents & social | `05_phase_C.md` |
| 6 | Phase A + grounded stories | `06_phase_A_stories.md` |
| 7 | Bridge | `07_bridge.md` |
| 8 | Phase D — processes & systems | `08_phase_D.md` |
| 9 | Phase E — abstraction | `09_phase_E.md` |

Sequence is a hypothesis, not a contract. Each eval decides whether the next step proceeds as planned.

---

## Standing work (lower urgency)

- [ ] Phase I — Corpus critic (`meta/scripts/corpus_critic.py`) — before any full-scale campaign
- [ ] Phase E — Wiki splitting (for finer curriculum ordering)
- [ ] Phase H — Ordering manifests (depends on Phase E)
- [ ] Fix `allowlist_rank` not propagating into JSONL units (cosmetic; doesn't affect training order)
