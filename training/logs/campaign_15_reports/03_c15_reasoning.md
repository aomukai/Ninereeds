# Campaign 15 — Block 3: Reasoning + Arithmetic Phase B

## Setup

| Field | Value |
|---|---|
| Campaign | 15 |
| Report | 03 — Reasoning corpus + arithmetic Phase B (paraphrase equivalence) |
| Model | 25M |
| Base checkpoint | `checkpoints/c15_arith_grounded_winner.pt` (arith_jp 0.984, shaped 0.976) |
| Corpus | `training/corpus/c15_reasoning_arithB.txt` |
| Corpus size | 73 files / 0.13 MB |
| Order file | `training/corpus_admin/campaign15_blocks/c15_thinking_03_reasoning_arithB.txt` |
| Shuffle | DISABLED |
| Optimizer | AdamW + adam8bit (bf16 AMP) |
| Batch size | 1 + `--grad-accum-steps 2` (VRAM constrained) |
| Epochs | 3 (~1 min/epoch; total training time ~3 min) |

## Motivation

Arithmetic Phase B (5 files) introduces paraphrase equivalence: same arithmetic facts expressed with varied question surface forms (e.g., "what is 3+4?" vs "3 plus 4 equals?"). This tests whether the hub pattern built in Phase A generalises across surface variation.

Reasoning corpus (68 files) covers operation facts, logic, and epistemic uncertainty. The combined corpus is small (73 files) but tightly targeted — the goal is hub consolidation, not new vocabulary acquisition.

## Results

| Epoch | Shaped | arith_jp after-hub | arith_zh after-hub | spatial after-hub |
|---|---|---|---|---|
| **E1** | 0.941 | **0.990** | **0.991** | 0.168 |
| E2 | 0.935 | 0.981 | 0.986 | 0.169 |
| E3 | **0.943** | 0.944 | 0.973 | 0.132 |

E1 has the highest arith_jp (0.990) and arith_zh (0.991). E3 has the highest shaped (0.943) but arith_jp collapses to 0.944 (−0.046 from E1). E2 is intermediate and dominated.

## Brain scan — thinking probe set (14 categories)

| Category | E1 after-hub | E2 after-hub | E3 after-hub |
|---|---|---|---|
| arithmetic_jp | **0.990** | 0.981 | 0.944 |
| arithmetic_zh | **0.991** | 0.986 | 0.973 |
| arithmetic_de | 0.953 | 0.923 | **0.934** |
| arithmetic | 0.797 | 0.749 | **0.821** |
| rule_application | 0.788 | **0.921** | 0.648 |
| contrastive | **0.851** | 0.635 | 0.665 |
| sequence | **0.529** | 0.510 | 0.529 |
| arithmetic_grounded | 0.623 | 0.579 | **0.723** |
| arithmetic_para | **0.484** | 0.271 | 0.409 |
| zero | 0.381 | **0.427** | 0.404 |
| comparison | **0.301** | 0.271 | 0.273 |
| successor | **0.229** | 0.195 | 0.232 |
| identity | **0.285** | 0.180 | 0.165 |
| grounded_causal | **0.189** | 0.147 | 0.200 |

## Winner selection

E1 selected: highest arith_jp (0.990) and arith_zh (0.991). E2 has a notable rule_application spike (0.921 vs E1's 0.788) but costs arith_jp (−0.009). E3 recovers arithmetic (0.821) and arithmetic_grounded (0.723) but arith_jp collapses to 0.944 (−0.046). E3's shaped gain (0.943 vs 0.941) is within noise and does not justify the arith_jp cost.

| Field | Value |
|---|---|
| Selected checkpoint | `core/c15_reasoning_e1.pt` |
| arith_jp after-hub | 0.990 |
| Shaped score | 0.941 |
| Saved to | `checkpoints/c15_reasoning_winner.pt` |

## Key observations

- **arith_jp (0.990) highest yet in C15** — Block 3 is the first time arith_jp exceeds 0.990. At this stage in C14c, arith_jp was 0.892.
- **E1 peak confirmed for 73-file focused block** — pattern holds: small focused blocks peak at E1. Large blocks (>10k files) peak at E2.
- **rule_application spike at E2 (0.921)** — interesting that reasoning corpus strengthens rule_application specifically. If rule_application matters for a future research question, a 2-epoch run on this block would be an option.
- **arith_para at E1 (0.484) then collapses** — paraphrase generalisation is fragile. The Phase B corpus (5 files) is too small to sustain hub connectivity past E1. Consider expanding Phase B before C16.
- **Spatial remains low (0.132–0.169)** — spatial hubs have not recovered since B1. Needs dedicated spatial block or corpus presence to rebuild.
