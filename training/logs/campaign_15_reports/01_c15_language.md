# Campaign 15 — Block 1: Language Core

## Setup

| Field | Value |
|---|---|
| Campaign | 15 |
| Report | 01 — Language core (EDJC-rotated full curriculum) |
| Model | 25M |
| Base checkpoint | `checkpoints/c13_Phase_C_winner.pt` (shaped 0.925) |
| Corpus | `training/corpus/campaign15_full.txt` |
| Corpus size | 42,021 files / 54.89 MB |
| Order file | `training/corpus_admin/campaign15_manifest.txt` |
| Shuffle | DISABLED (`--no-shuffle`) |
| Optimizer | AdamW (bf16 AMP) |
| Batch size | 4 |
| LR | 1e-3 (cosine decay) |
| Epochs | 3 |
| Eval | 4-lingual (72 prompts = 18 slots × EN/DE/JP/ZH) |

## Motivation

C14's language block (C14a/b) was trained without EDJC rotation on an EN-only eval (18 prompts).
C15 retrains from scratch on the full rotated corpus so that EDJC language-order cycling propagates
through Hebbian co-firing from the very first epoch. Goal: stronger per-language circuits from
the ground up, especially JP/ZH which consistently lagged.

**EDJC rotation:** corpus files have language order cycled across EDJC/DJCE/JCED/CEDJ patterns
to prevent EN/DE from always occupying the first (highest Hebbian weight) position.

## Corpus note

Initial launch used `--corpus-file training/corpus_admin/campaign15_manifest.txt` directly.
`train.py` reads `--corpus-file` as raw bytes — passing a manifest trains on file path strings,
not content. Detected immediately (eval completions output file paths). Bad checkpoints removed.
Corpus rebuilt with `build_training_corpus.py --order-file campaign15_manifest.txt` →
`training/corpus/campaign15_full.txt` (54.89 MB, 0 skipped, all validated). Training relaunched
from correct corpus.

## Results

| Epoch | Shaped | EN | DE | JP | ZH | EN floor | DE floor | JP floor | ZH floor |
|---|---|---|---|---|---|---|---|---|---|
| E1 | 0.953 | 0.982 | 0.973 | 0.909 | 0.949 | 0.85 | 0.85 | 0.76 | 0.79 |
| **E2** | **0.958** | 0.983 | **0.978** | **0.929** | 0.942 | 0.85 | 0.85 | 0.79 | 0.79 |
| E3 | 0.956 | **0.990** | 0.972 | 0.909 | **0.952** | 0.85 | 0.85 | 0.79 | 0.82 |

E3 gains EN (+0.007) and ZH (+0.010) but JP regresses to E1 level (0.929→0.909).
Pattern matches C14c: E2 is the productive peak before LR-bottom instability sets in.

## Brain scan summary

### Language probe set (16 categories)

| Category | E1 after-hub | E2 after-hub | E3 after-hub | Peak |
|---|---|---|---|---|
| emotions_boolean | 0.845 | 0.765 | 0.818 | E1 |
| cognitive | 0.654 | 0.670 | **0.800** | E3 |
| vehicles | 0.807 | **0.894** | 0.698 | E2 |
| objects | 0.712 | **0.820** | 0.674 | E2 |
| animals | 0.665 | **0.786** | 0.566 | E2 |
| emotions | 0.723 | **0.774** | 0.670 | E2 |
| movement | 0.381 | 0.402 | **0.553** | E3 |
| emotions_boundary | 0.260 | 0.269 | **0.366** | E3 |
| abstract | 0.531 | 0.432 | 0.468 | E1 |
| boundary | 0.385 | **0.473** | 0.269 | E2 |
| animals_boolean | 0.457 | **0.462** | 0.384 | E2 |
| grammar | 0.207 | 0.282 | **0.308** | E3 |
| time | 0.166 | 0.175 | **0.223** | E3 |
| spatial | 0.125 | **0.191** | 0.135 | E2 |
| multilingual | 0.208 | 0.186 | 0.201 | E1 |
| arithmetic | 0.134 | **0.218** | 0.140 | E2 |

### Thinking probe set (14 categories)

| Category | E1 after-hub | E2 after-hub | E3 after-hub | Peak |
|---|---|---|---|---|
| arithmetic_jp | 0.980 | **0.987** | 0.967 | E2 |
| arithmetic_zh | 0.960 | **0.963** | 0.936 | E2 |
| arithmetic_de | 0.921 | 0.893 | **0.904** | E1 |
| arithmetic | 0.906 | 0.801 | 0.781 | E1 |
| contrastive | 0.643 | **0.841** | 0.633 | E2 |
| rule_application | 0.649 | **0.728** | 0.728 | E2/E3 |
| sequence | 0.539 | 0.522 | **0.535** | E1 |
| arithmetic_grounded | 0.517 | 0.379 | **0.392** | E1 |
| arithmetic_para | 0.337 | **0.348** | 0.325 | E2 |
| zero | 0.347 | 0.330 | **0.340** | E1 |
| grounded_causal | 0.239 | 0.202 | **0.230** | E1 |
| identity | 0.348 | 0.155 | 0.198 | E1 |
| comparison | 0.328 | 0.193 | 0.192 | E1 |
| successor | 0.156 | 0.196 | **0.187** | E2 |

### E2 vs E3 decision

E3 trades arithmetic_jp (0.987→0.967), arithmetic_zh (0.963→0.936), spatial (0.191→0.135),
and contrastive (0.841→0.633) for gains in cognitive, movement, grammar, and time.
JP shaped score regression (0.929→0.909) matches the arithmetic_jp circuit collapse.
**E2 selected.**

## Key findings

- **arithmetic_jp at E2: 0.987** — significantly above C14c peak of 0.912 (at vignettes stage, 4 blocks later). EDJC rotation is improving JP arithmetic circuits at the language-core stage.
- **arithmetic_zh at E2: 0.963** — also improved vs C14c.
- **JP shaped at E2: 0.929** — highest JP score seen at language-block stage. C14a/b used EN-only eval so no direct comparison exists, but 0.929 vs EN 0.983 (gap 0.054) is a tighter gap than C14c Block 1 had before rotation was introduced.
- **E2 peak pattern confirmed** — second consecutive campaign showing E2 as productive peak, E3 as LR-bottom regression. Now a reliable rule: run 3 epochs, pick E2 unless brain scan shows a clear E3 advantage.
- **contrastive spike at E2** (0.643→0.841) then collapses at E3 (0.633) — watching whether this recovers in Block 2.

## Winner

| Field | Value |
|---|---|
| Selected checkpoint | `core/c15_language_e2.pt` |
| Shaped score | 0.958 (EN 0.983, DE 0.978, JP 0.929, ZH 0.942) |
| Rationale | JP shaped peak (0.929); arithmetic_jp after-hub peak (0.987); spatial and contrastive peaks. E3 JP regression to 0.909 matched arithmetic_jp collapse (0.987→0.967). |
| Saved to | `checkpoints/c15_language_winner.pt` |
