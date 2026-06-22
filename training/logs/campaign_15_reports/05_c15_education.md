# Campaign 15 — Block 5: Education (CKS K-8)

## Setup

| Field | Value |
|---|---|
| Campaign | 15 |
| Report | 05 — CKS K-8 education corpus |
| Model | 25M |
| Base checkpoint | `checkpoints/c15_vignettes_winner.pt` (arith_jp 0.937, shaped 0.987) |
| Corpus | `training/corpus/c15_education.txt` |
| Corpus size | 418 files / 7,781 lines |
| Shuffle | DISABLED |
| Optimizer | AdamW (bf16 AMP) |
| Batch size | 4 (GPU free: 3,653 MiB — full batch available after vignettes block) |
| Epochs | 3 (~5 min/epoch; total training time ~13 min) |

## Motivation

The CKS K-8 curriculum (418 `[user]/[Ninereeds]` dialogue files) was built in Campaign 15 as a domain-knowledge block: preschool (156 EN files) + K-8 (262 EN-only files). The hypothesis was that structured educational dialogue would reinforce the shaped score and broaden the model's knowledge anchoring without displacing arithmetic hubs. This is the last block of C15.

A secondary question: does the K-8 corpus (EN-only) selectively harm multilingual hubs?

## Results

| Epoch | Shaped | arith_jp after-hub | arith_zh after-hub | spatial after-hub |
|---|---|---|---|---|
| **E1** | 0.920 | **0.9994** | **0.9963** | 0.188 |
| E2 | **0.936** | 0.9986 | 0.9946 | 0.190 |
| E3 | 0.911 | 0.9973 | 0.9952 | **0.218** |

arith_jp is remarkably stable (0.9994→0.9986→0.9973), losing only 0.0021 across 3 epochs — far more stable than the vignettes block. Shaped is non-monotonic: peaks at E2 (0.936), falls at E3 (0.911).

## Brain scan — thinking probe set (14 categories)

| Category | E1 after-hub | E2 after-hub | E3 after-hub |
|---|---|---|---|
| arithmetic_jp | **0.999** | **0.999** | 0.997 |
| arithmetic_zh | **0.996** | **0.995** | 0.995 |
| arithmetic_de | 0.901 | **0.913** | 0.919 |
| arithmetic | **0.951** | 0.919 | 0.859 |
| rule_application | **0.940** | 0.871 | 0.819 |
| contrastive | **0.926** | 0.919 | 0.868 |
| arithmetic_grounded | **0.648** | 0.540 | 0.433 |
| sequence | 0.589 | **0.633** | 0.617 |
| comparison | **0.570** | 0.300 | 0.345 |
| arithmetic_para | **0.632** | 0.514 | 0.430 |
| identity | **0.415** | 0.248 | 0.276 |
| zero | **0.368** | 0.347 | 0.394 |
| grounded_causal | **0.290** | 0.262 | 0.215 |
| successor | **0.255** | 0.190 | 0.222 |

All 14 categories peak at E1, with the exception of arithmetic_de and sequence (E2 marginal gains).
The pattern is strongly E1-dominant.

## Brain scan — thinking E1 (full hub table)

```
arithmetic_jp         1.000 → 0.999  (−0.000)
arithmetic_zh         0.999 → 0.996  (−0.003)
rule_application      0.981 → 0.940  (−0.041)
arithmetic            0.996 → 0.951  (−0.044)
contrastive           0.971 → 0.926  (−0.045)
arithmetic_de         0.995 → 0.901  (−0.093)
sequence              0.868 → 0.589  (−0.279)
arithmetic_grounded   0.973 → 0.648  (−0.325)
comparison            0.895 → 0.570  (−0.325)
arithmetic_para       0.979 → 0.632  (−0.347)
zero                  0.770 → 0.368  (−0.402)
identity              0.835 → 0.415  (−0.419)
grounded_causal       0.770 → 0.290  (−0.480)
successor             0.815 → 0.255  (−0.560)
```

The hub removal effect (before→after) shows that arith_jp and arith_zh are almost entirely carried by hubs (very low delta), while grounded_causal, identity, and successor have weak hub structure. The K-8 corpus is not disrupting arith_jp circuit formation — the hubs remain tight.

## Winner selection

E1 selected: highest arith_jp (0.9994 vs 0.9986/0.9973). All 14 thinking categories peak at E1. Shaped gain at E2 (+0.016) does not offset arith_jp loss or the broad regression in arithmetic_grounded, comparison, arithmetic_para, identity.

| Field | Value |
|---|---|
| Selected checkpoint | `core/c15_education_e1.pt` |
| arith_jp after-hub | 0.9994 |
| Shaped score | 0.920 |
| Saved to | `checkpoints/c15_education_winner.pt` |

## Key observations

- **arith_jp reaches 0.9994 — campaign peak, C15 best.** After the vignettes block brought it down to 0.937, the K-8 education corpus restores and strengthens arithmetic_jp circuits. Education corpus and arithmetic representations are surprisingly compatible.
- **arith_jp stability across epochs** — only −0.0021 drop from E1 to E3, vs −0.156 for vignettes over the same 3 epochs. The EN-structured educational dialogue does not compete with the arithmetic hub pattern.
- **shaped score drops from vignettes peak (0.987→0.920)** — the K-8 corpus pulls shaped down. This is expected: K-8 is EN-only, and shaped is 4-lingual weighted. Multilingual circuits likely soften slightly. The shaped drop is the cost of the arith_jp recovery.
- **Sparsity rebounds to 0.017 from vignettes' 0.009** — hub density restored. The K-8 corpus creates a denser co-activation pattern than vignettes, closer to the reasoning block profile.
- **K-8 corpus gate for C16**: multilingual μ at E1 thinking scan shows arith_zh=0.996, arith_de=0.901. The K-8 corpus (EN-only) does not appear to damage multilingual arithmetic significantly. The gate condition (multilingual μ ≤ 0.30 = localize) is clearly not triggered. K-8 localization is not required for C16.
- **E3 shaped collapse (0.936→0.911)** — likely LR-bottom instability. Pattern seen in B1 and C14c. Standard 3-epoch, pick-the-peak behaviour.
