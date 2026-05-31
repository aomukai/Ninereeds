# Campaign 13 — Phase A report

## Setup

| Field | Value |
|---|---|
| Campaign | 13 |
| Report | 01 — Phase A (concrete anchors) |
| Model | 25M (default — no scale flag) |
| Base checkpoint | fresh start |
| Corpus | `training/corpus/campaign_13_phase_A.txt` |
| Corpus size | 5.70 MB / 6,464 files |
| Order file | `training/training_order/phase_A_order.jsonl` |
| Optimizer | AdamW (bf16 AMP) |
| LR | 1e-3 (cosine decay) |
| GPU | GPU 0 (dedicated training card, RTX 3060 12GB) |

## Strategy

Two variants trained and compared; winner becomes the base for Phase B:

| Variant | Corpus | Checkpoint |
|---|---|---|
| A | Phase A only | `campaign_13_phase_A.pt` |
| A+BR | Phase A → Bridge | `campaign_13_phase_A_bridge.pt` |

Train each variant until regression (shaped score drops two consecutive epochs).
Pick the epoch with the highest shaped score from each variant, compare, advance the winner.

---

## Variant A — Phase A only

### Per-epoch results

| Epoch | Loss | Raw | Shaped | Δ Shaped | Loops | Abrupt | Notes |
|---|---|---|---|---|---|---|---|
| E1 | 1.3251 | 0.910 | 0.906 | — | 2 | 0 | Adam warmup noise |
| E2 | 0.7214 | 0.894 | 0.903 | -0.003 | 5 | 0 | Loop spike; shaped dipped |
| E3 | 0.5862 | 0.900 | 0.914 | +0.011 | 2 | 0 | Recovery; loss still dropping |
| E4 | 0.6652 | 0.918 | 0.907 | -0.007 | 4 | 0 | batch=4 (OOM at batch=8; single GPU) |
| E5 | (log TBD) | 0.904 | 0.900 | -0.007 | 2 | 0 | 2nd consecutive drop; regression confirmed |

Add rows as needed. Stop when shaped score drops two consecutive epochs.

### Probe results per epoch

**E1** — FC 1/8 · garbled 1/17 · sentences 16/17 · pronouns 0 · negation 0 · arith 0/3 · dative über 0/3
- FC pass: acc movement only
- Format: good structure, acorn/bright/battling producing phase-format lines
- Arithmetic: not in Phase A corpus — all fail expected
- Dative: not in Phase A corpus — all fail expected

**E2** — FC 3/8 · garbled 1/17 · sentences 16/17 · pronouns 0 · negation 0 · arith 0/3 · dative über 0/3
- FC pass: dative über (dem Boden ✓), acc movement, JP autumn
- Dative FC passes but randomised dative probes still 0/3 — not generalising yet

**E3** — FC 3/8 · garbled 1/17 · sentences 16/17 · pronouns 0 · negation 0 · arith 0/3 · dative über 0/3
- FC pass: dative über (den Körper — accusative, FC threshold met), acc movement, JP autumn
- Acorn probe: 6 clean property lines — best format quality yet
- Battling: using "Batt" truncation — format routing slightly degraded vs E1

### Best checkpoint

| Field | Value |
|---|---|
| Selected epoch | E3 |
| Reason | Highest shaped (0.914); loops back to 2; E4 and E5 both dropped (0.907, 0.900) |
| Checkpoint path | `core/campaign_13_phase_A_e3.pt` |
| Saved to | `checkpoints/c13_phaseA_winner.pt` (promoted by orchestrator) |

---

## Variant A+BR — Phase A → Bridge

Train bridge on top of Variant A best checkpoint.

```bash
CUDA_VISIBLE_DEVICES=0 nohup /home/aomukai/.unsloth/studio/unsloth_studio/bin/python train.py \
  --phase 0 \
  --corpus-file training/corpus/campaign_13_bridge.txt \
  --output core/campaign_13_phase_A_bridge.pt \
  --resume checkpoints/c13_phase_A_eN.pt \
  --epochs 2 --epoch-checkpoints --amp-bf16 \
  > training/logs/campaign_13_reports/phase_A_bridge_train.log 2>&1 &
```

(Build bridge corpus first: `--order-file training/training_order/bridge_order.jsonl`)

### Per-epoch results

| Epoch | Loss | Raw | Shaped | Δ vs A-best | Loops | Abrupt | Notes |
|---|---|---|---|---|---|---|---|
| E1 | (fill) | (fill) | (fill) | (fill) | (fill) | (fill) | |
| E2 | (fill) | (fill) | (fill) | (fill) | (fill) | (fill) | |

### Probe results — best epoch

```
(paste probe.py output here)
```

### Best checkpoint

| Field | Value |
|---|---|
| Selected epoch | (fill) |
| Reason | (fill) |
| Checkpoint path | `core/campaign_13_phase_A_bridge_eN.pt` |
| Saved to | `checkpoints/c13_phase_A_bridge_eN.pt` |

---

## A vs A+BR comparison

| Metric | Variant A | Variant A+BR | Winner |
|---|---|---|---|
| Peak shaped | (fill) | (fill) | (fill) |
| Loops | (fill) | (fill) | (fill) |
| Abrupt stops | (fill) | (fill) | (fill) |
| Format quality | (fill) | (fill) | (fill) |

**Winner:** (fill)
**Foundation for Phase B:** `checkpoints/(fill)`

**Observations:**
(What did Phase A teach? What's clearly learned? What's still absent or broken?)

---

## Probe commands

```bash
# Run after each epoch checkpoint appears
CKPT=core/campaign_13_phase_A_eN.pt
/home/aomukai/.unsloth/studio/unsloth_studio/bin/python meta/scripts/probe.py \
  --checkpoint "$CKPT" --temperature 0.7 --tokens 120

/home/aomukai/.unsloth/studio/unsloth_studio/bin/python eval.py --checkpoint "$CKPT"
```
