# Campaign 15 — Block 4: Vignettes

## Setup

| Field | Value |
|---|---|
| Campaign | 15 |
| Report | 04 — Vignettes corpus |
| Model | 25M |
| Base checkpoint | `checkpoints/c15_reasoning_winner.pt` (arith_jp 0.990, shaped 0.941) |
| Corpus | `training/corpus/c15_vignettes.txt` |
| Corpus size | 2,048 files (clean, post-audit) |
| Shuffle | DISABLED |
| Optimizer | AdamW + adam8bit (bf16 AMP) |
| Batch size | 1 + `--grad-accum-steps 2` (VRAM constrained; GPU 0 free: 1,564 MiB) |
| Epochs | 3 (~22 min/epoch; total training time ~33 min) |

## Motivation

Vignettes are short scenario-based corpus items designed to build contextual reasoning and narrative coherence. At C14c the vignettes block improved shaped score significantly but the brain scan (C14c block 3 analysis) showed shaped gains came with arith_jp trade-offs. Hypothesis: vignettes displace arithmetic hub connectivity because the narrative style is structurally dissimilar to the tightly formatted arithmetic drills.

## Results

| Epoch | Shaped | arith_jp after-hub | arith_zh after-hub | spatial after-hub |
|---|---|---|---|---|
| **E1** | 0.987 | **0.937** | 0.940 | **0.196** |
| E2 | **0.989** | 0.860 | **0.921** | 0.149 |
| E3 | 0.986 | 0.781 | 0.895 | 0.179 |

arith_jp collapses monotonically: 0.937 → 0.860 → 0.781 (−0.077/epoch, −0.156 total over 3 epochs).
Shaped score is nearly flat across all three epochs (0.987/0.989/0.986).

## Brain scan — thinking probe set (14 categories)

| Category | E1 after-hub | E2 after-hub | E3 after-hub |
|---|---|---|---|
| arithmetic_jp | **0.937** | 0.860 | 0.781 |
| arithmetic_zh | 0.940 | **0.921** | 0.895 |
| arithmetic_de | **0.747** | 0.725 | 0.690 |
| arithmetic | 0.662 | **0.699** | 0.624 |
| rule_application | 0.747 | **0.828** | 0.782 |
| contrastive | 0.600 | **0.642** | 0.697 |
| sequence | **0.511** | 0.460 | 0.371 |
| zero | 0.337 | **0.496** | 0.308 |
| arithmetic_grounded | 0.229 | **0.565** | 0.458 |
| arithmetic_para | **0.226** | 0.313 | 0.217 |
| successor | **0.319** | 0.310 | 0.205 |
| comparison | 0.204 | **0.304** | 0.155 |
| grounded_causal | 0.162 | **0.229** | 0.222 |
| identity | **0.175** | 0.187 | 0.166 |

## Winner selection

E1 selected: arith_jp (0.937) is the primary criterion; E2 and E3 are lower. E2 has higher shaped (0.989 vs 0.987) and higher arith_zh (0.921 vs 0.940 — wait, E1 arith_zh 0.940 > E2 0.921), rule_application, and arithmetic_grounded, but arith_jp is irreversibly lower. Shaped gain at E2 (+0.002) is negligible.

| Field | Value |
|---|---|
| Selected checkpoint | `core/c15_vignettes_e1.pt` |
| arith_jp after-hub | 0.937 |
| Shaped score | 0.987 |
| Saved to | `checkpoints/c15_vignettes_winner.pt` |

## Key observations

- **CONFIRMED: vignettes cap at 1 epoch.** arith_jp drops −0.077 per epoch (0.937→0.860→0.781). Three epochs would cost −0.156 arith_jp for a shaped gain of essentially zero (0.987→0.986). This is a hard rule for all future campaigns: vignettes block = 1 epoch.
- **shaped score is not a useful signal for this block** — E1/E2/E3 shaped scores differ by ≤0.003. Shaped is nearly insensitive to the vignettes corpus. Only the brain scan distinguishes epochs.
- **hub count drops markedly vs B3**: E1 routing hubs = 2,121 (vs 3,938 in B3 E1). Vignettes produce sparser hub patterns — consistent with the narrative style spreading activation more broadly rather than concentrating in tight arithmetic clusters.
- **sparsity drops at vignettes** (avg sparsity 0.009 vs 0.018–0.019 in B3) — fewer neurons active per probe. The vignette style is activating a different, less overlapping set of representations.
- **rule_application recovers at E2 (0.828)** but arith_jp is already below threshold. Not actionable within this block.
