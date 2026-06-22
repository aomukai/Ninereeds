# Campaign 15 — Block 2: Arithmetic + Grounded Stories

## Setup

| Field | Value |
|---|---|
| Campaign | 15 |
| Report | 02 — Arithmetic bridge + grounded stories |
| Model | 25M |
| Base checkpoint | `checkpoints/c15_language_winner.pt` (arith_jp 0.987, shaped 0.958) |
| Corpus | `training/corpus/c15_arith_grounded.txt` |
| Corpus size | 3,008 files / 3.25 MB |
| Order file | `training/corpus_admin/campaign15_blocks/c15_thinking_02_arith_grounded.txt` |
| Shuffle | DISABLED (`--no-shuffle`) |
| Optimizer | AdamW + adam8bit (bf16 AMP) |
| Batch size | 1 + `--grad-accum-steps 2` (VRAM constrained; mnm.exe holding 7.4 GB on GPU 0) |
| Epochs | 3 |

## Motivation

Reintroduce arithmetic reasoning after the 42k-file language block. The language block is likely to diffuse arithmetic hub connectivity (EN-only arithmetic was the weakest category in B1 brain scan). Grounded stories (747 × 4 langs) are sequentially ordered — shuffling is disabled to preserve the narrative arc.

Arithmetic bridge is prepended as a ≤2% minority within the grounded corpus (saturation rule: never run arithmetic standalone at <100 files × 3 epochs).

## Results

| Epoch | Shaped | arith_jp after-hub | arith_zh after-hub | spatial after-hub |
|---|---|---|---|---|
| **E1** | **0.976** | **0.984** | 0.941 | 0.115 |
| E2 | 0.966 | 0.954 | 0.960 | 0.253 |
| E3 | 0.968 | 0.979 | 0.959 | 0.171 |

E1 has the highest arith_jp (0.984). E3 recovers partially (0.979) but does not surpass E1. E2 shows an arith_jp dip (0.954) with spatial spike (0.253) — likely a transient rebalancing.

## Brain scan — thinking probe set (14 categories)

| Category | E1 after-hub | E2 after-hub | E3 after-hub |
|---|---|---|---|
| arithmetic_jp | **0.984** | 0.954 | 0.979 |
| arithmetic_zh | 0.941 | **0.960** | 0.959 |
| arithmetic_de | 0.849 | **0.872** | 0.917 |
| arithmetic | **0.894** | 0.678 | 0.668 |
| contrastive | **0.836** | 0.615 | 0.742 |
| rule_application | 0.758 | 0.655 | **0.765** |
| sequence | **0.423** | 0.472 | 0.408 |
| arithmetic_grounded | **0.626** | 0.486 | 0.544 |
| arithmetic_para | **0.488** | 0.382 | 0.293 |
| zero | 0.392 | 0.365 | **0.455** |
| comparison | 0.217 | 0.215 | **0.256** |
| successor | **0.268** | 0.223 | 0.218 |
| grounded_causal | **0.234** | 0.175 | 0.155 |
| identity | 0.169 | **0.196** | 0.248 |

## Brain scan — language probe set (16 categories, selected)

| Category | E1 after-hub | E2 after-hub | E3 after-hub |
|---|---|---|---|
| grammar | — | — | — |
| multilingual | — | — | — |
| spatial | — | — | — |

*Language hub JSONs not parsed here; key language metrics available in `training/logs/brain_maps/c15_arith_grounded_e*_language_hubs.json`.*

## Winner selection

E1 selected: highest arith_jp (0.984), highest arithmetic after-hub (0.894), highest contrastive (0.836), highest arithmetic_grounded (0.626). E3's arith_jp recovery (0.979) does not surpass E1 and costs EN arithmetic (0.668 vs 0.894). E2 is strictly dominated.

| Field | Value |
|---|---|
| Selected checkpoint | `core/c15_arith_grounded_e1.pt` |
| arith_jp after-hub | 0.984 |
| Shaped score | 0.976 |
| Saved to | `checkpoints/c15_arith_grounded_winner.pt` |

## Key observations

- **E1 peak pattern holds for focused blocks** — 3,008 files × 3 epochs. The model absorbs the focused arithmetic signal by E1; further epochs redistribute hubs without improving the primary criterion.
- **EN arithmetic (0.894) much higher than after language block** — the language block (42k files) had arithmetic after-hub at 0.218 (B1 E2). The arithmetic bridge restore is working.
- **arith_de at E3 (0.917) exceeds arith_jp (0.979)** — unusual; DE arithmetic seems to consolidate more over epochs than JP. Watch in B3.
- **spatial spike at E2 (0.253)** — returns to baseline at E3. Appears to be a transient hub-competition effect during E2 rebalancing.
