# Campaign 14c — Vignettes + Grounded Scale-up

## Setup

| Field | Value |
|---|---|
| Campaign | 14c |
| Report | 03 — Vignettes + grounded stories scale-up |
| Model | 25M (default — no scale flag) |
| Base checkpoint | `checkpoints/c14_winner.pt` (C14b-E1, shaped 0.934) |
| Batch size | 4 (reduced from default 8 — GPU shared this weekend) |
| Shuffle | DISABLED (`--no-shuffle`) on all thinking blocks |
| Optimizer | AdamW (bf16 AMP) |
| LR | 1e-3 (cosine decay) |
| Epochs | 3 per block |
| GPU | CUDA:0 (RTX 3060 12GB, shared with user workload this weekend) |

## Base checkpoint selection (C14 eval summary)

All 6 C14 epoch checkpoints evaluated before this run:

| Checkpoint | Shaped | Loops | Notes |
|---|---|---|---|
| C14a-E1 | 0.928 | 0 | |
| C14a-E2 | 0.930 | 0 | A peak |
| C14a-E3 | 0.917 | 0 | regression |
| C14b-E1 | **0.934** | **0** | **WINNER — tighter floor (0.80 worst)** |
| C14b-E2 | 0.934 | 0 | tied shaped; worse floor (0.75 worst: 'If I could change one thing') |
| C14b-E3 | 0.917 | 0 | regression |

Winner: `core/campaign14b_full_e1.pt` → promoted to `checkpoints/c14_winner.pt`.
Tiebreaker over C14b-E2: worst-prompt floor 0.80 vs 0.75; C14b-E1 has tighter per-prompt variance.

## New corpus blocks since C14a/b

| Block | Files | Size | What's new |
|---|---|---|---|
| c14_03 grounded stories | 2,988 | 3.20 MB | Expanded 195→747 stories; 10 new groups, new cast/locations |
| c14_05 vignettes | 2,048 | 1.65 MB | Sentence-rotation; 5 syntactic angles × 4 languages per file; language order rotates to prevent positional bias |

## Hypothesis

- **Vignettes** force Hebbian circuits to extract the semantic invariant (same event, varied surface) rather than memorise surface form. Expected improvement: grammar μ and spatial μ in brain_map.
- **Grounded story scale-up** (4× more stories, new locations/characters) improves causal reasoning and multilingual coverage, especially JP/ZH which has been flat at ~0.20 μ.

## Block order (C14c)

All thinking blocks use `--no-shuffle`. Language core (c14_01) already trained in C14a/b — not repeated here. This run trains the thinking blocks only on top of the C14 language checkpoint.

**Revised after arith standalone failure:**

1. ~~`c14_02_arithmetic_bridge.txt` standalone~~ — ABANDONED. 20 files × 3 epochs = 100% arithmetic saturation → shaped 0.867/0.866/0.863 (base was 0.934). Arithmetic format bled into all general completions. Same pattern as run_2 story catastrophe. Rule confirmed: never run a tiny single-format block as a standalone pass.
2. `c14c_arith_grounded.txt` — arith (20 files, 56 KB) prepended to grounded stories (2,988 files, 3.20 MB) = 3,008 files, 3.25 MB total. Arith = 1.6% of block. Base: `c14_winner.pt`.
3. `c14_04_reasoning.txt` — 68 files, 124 KB. Base: best grounded epoch.
4. `c14_05_vignettes.txt` — 2,048 files, 1.65 MB. Base: best reasoning epoch.
5. `c14c_education.txt` — 418/418 education dialogues, 0.63 MB. Base: best vignettes epoch. Added to observe effect on conversational language ability and question-forming register. All 33 mismatched files repaired by DeepSeek (meta/scripts/repair_education_mismatches.py) and corpus rebuilt.

## Launch commands

```bash
PYTHON=/home/aomukai/.unsloth/studio/unsloth_studio/bin/python
BASE=checkpoints/c14_winner.pt

# Block 1 — arithmetic bridge
CUDA_VISIBLE_DEVICES=0 nohup $PYTHON train.py \
  --phase 0 \
  --corpus-file training/corpus/c14_02_arithmetic_bridge.txt \
  --output core/c14c_arith.pt \
  --resume $BASE \
  --epochs 3 --epoch-checkpoints --amp-bf16 --no-shuffle --batch-size 4 \
  > training/logs/campaign_14_reports/03_c14c_arith_train.log 2>&1 &
echo "PID: $!"

# Block 2 — grounded stories (use best arith checkpoint as base)
CUDA_VISIBLE_DEVICES=0 nohup $PYTHON train.py \
  --phase 0 \
  --corpus-file training/corpus/c14_03_grounded_stories.txt \
  --output core/c14c_grounded.pt \
  --resume core/c14c_arith_eK.pt \
  --epochs 3 --epoch-checkpoints --amp-bf16 --no-shuffle --batch-size 4 \
  > training/logs/campaign_14_reports/03_c14c_grounded_train.log 2>&1 &

# Block 3 — reasoning
CUDA_VISIBLE_DEVICES=0 nohup $PYTHON train.py \
  --phase 0 \
  --corpus-file training/corpus/c14_04_reasoning.txt \
  --output core/c14c_reasoning.pt \
  --resume core/c14c_grounded_eK.pt \
  --epochs 3 --epoch-checkpoints --amp-bf16 --no-shuffle --batch-size 4 \
  > training/logs/campaign_14_reports/03_c14c_reasoning_train.log 2>&1 &

# Block 4 — vignettes
CUDA_VISIBLE_DEVICES=0 nohup $PYTHON train.py \
  --phase 0 \
  --corpus-file training/corpus/c14_05_vignettes.txt \
  --output core/c14c_vignettes.pt \
  --resume core/c14c_reasoning_eK.pt \
  --epochs 3 --epoch-checkpoints --amp-bf16 --no-shuffle --batch-size 4 \
  > training/logs/campaign_14_reports/03_c14c_vignettes_train.log 2>&1 &
```

Monitor for first epoch:
```bash
until [ -f core/c14c_arith_e1.pt ]; do sleep 60; done && echo "arith E1 ready"
```

## Eval commands (after each epoch checkpoint)

**eval.py upgraded to 4-lingual format during C14c** (2026-06-20):
- 72 prompts = 18 semantic slots × 4 languages (EN / DE / JP / ZH)
- Scorer is now language-agnostic (unicodedata instead of ASCII-only checks)
- Reports per-language shaped averages; EN section is historically comparable
- Block 1–3 results above used the old 18-prompt EN-only eval

```bash
CKPT=core/c14c_vignettes_eK.pt   # substitute block and epoch
PYTHON=/home/aomukai/.unsloth/studio/unsloth_studio/bin/python

$PYTHON eval.py --checkpoint "$CKPT"

$PYTHON meta/scripts/probe.py --checkpoint "$CKPT" --temperature 0.7 --tokens 120

$PYTHON meta/scripts/brain_map.py probe \
  --checkpoint "$CKPT" \
  --probes training/corpus_admin/probe_sets/language.jsonl \
  --name c14c_vignettes_eK_language

$PYTHON meta/scripts/brain_map.py probe \
  --checkpoint "$CKPT" \
  --probes training/corpus_admin/probe_sets/thinking.jsonl \
  --name c14c_vignettes_eK_thinking

$PYTHON meta/scripts/brain_map.py hubs --name c14c_vignettes_eK_language --threshold 0.7
$PYTHON meta/scripts/brain_map.py hubs --name c14c_vignettes_eK_thinking --threshold 0.7
```

---

## Per-block results

### Block 1 — Arithmetic bridge (standalone) — ABANDONED

| Epoch | Loss | Shaped | Raw | Loops | Notes |
|---|---|---|---|---|---|
| E1 | 1.045 | 0.867 | 0.873 | 0 | Arith format bleeding into all prompts |
| E2 | 0.575 | 0.866 | 0.859 | 0 | No improvement |
| E3 | 0.398 | 0.863 | 0.854 | 0 | Worse floor (0.71 worst prompt) |

**Finding:** 100% arithmetic saturation (20 files × 3 epochs) collapsed shaped score from 0.934 → 0.863–0.867. Model output arithmetic tokens in response to narrative/emotional prompts ('She was afraid because' → 'six. jp: 二を除き三と同じです。'). Same failure mode as run_2 story catastrophe. No epoch promoted. Proceeding from `c14_winner.pt`.

**Rule confirmed:** never run a single-format block of <100 files as a standalone pass. Interleave at ≤5% of a larger corpus.

### Block 2 — Arith+Grounded (c14c_arith_grounded.txt)

Base: `checkpoints/c14_winner.pt` (0.934)

| Epoch | Shaped | Raw | Loops | Abrupt | Notes |
|---|---|---|---|---|---|
| E1 | 0.940 | 0.939 | 0 | 0 | New high. Story char/location bleed (Yun/Mei/mill/potato) — normal E1. Causal +0.158 ('rainbow'). Persistent weak: 'If I could change' 0.77. |
| E2 | **0.946** | 0.937 | 0 | 0 | New high. Floor lifted: worst 0.91 (vs 0.77 E1). Bleed settling. 'If I could change' recovered (+0.025). Causal +0.047 ('rainbow'), +0.041 ('afraid'). |
| E3 | 0.938 | 0.938 | 0 | 0 | Regression. 'The reason I like reading is' −0.130 (floor 0.80). Typical E3 LR-bottom instability. |

Best checkpoint: **`core/c14c_grounded_e2.pt`** (shaped 0.946, floor 0.91)

### Block 3 — Reasoning + ArithB (c14c_reasoning_arithB.txt, 73 files)

Base: `core/c14c_grounded_e2.pt` (0.946)

| Epoch | Shaped | Raw | Notes |
|---|---|---|---|
| E1 | 0.828 | 0.862 | Big regression. Q&A format floods narrative: 'rainbow' 0.46, 'birds' 0.68. ArithB Q: pattern competing with causal completions. |
| E2 | 0.872 | 0.800 | Recovery. Floor: 'Language' 0.70, 'birds' 0.73. |
| E3 | **0.891** | 0.847 | Best. Floor: 'Language' 0.79 (weakest). 'Rainbow' 0.81, all Q: probes recovering. |

Best checkpoint: **`core/c14c_reasoning_e3.pt`** (shaped 0.891)

### Block 4 — Vignettes (c14_05_vignettes.txt, 2048 files)

Base: `core/c14c_reasoning_e3.pt` (0.891 old eval)
**First block evaluated with 4-lingual eval (72 prompts = 18 slots × EN/DE/JP/ZH).**

| Epoch | Shaped | EN | DE | JP | ZH | Notes |
|---|---|---|---|---|---|---|
| E1 | 0.989 | 0.996 | 0.978 | 0.986 | 0.996 | Raw=shaped (delta 0.000): model no longer needs shaping running-start. DE floor 0.93. |
| E2 | 0.989 | 0.996 | 0.983 | 0.980 | 0.997 | DE improving (+0.005). JP -0.006 (minor). DE floor lifted to 0.95. |
| E3 | **0.990** | **0.997** | **0.985** | 0.979 | **0.998** | Best overall. JP stable at 0.979 floor 0.94. ZH 0.998 near-perfect. |

Best checkpoint: **`core/c14c_vignettes_e3.pt`** (shaped 0.990, EN 0.997, DE 0.985, JP 0.979, ZH 0.998)

Key finding: vignettes training produced a marked jump in multilingual generation quality across all scripts. Raw ≈ shaped throughout — the model is generating clean text without needing a prompted running-start. JP is the weakest language (0.979 vs DE 0.985, ZH 0.998) and is the primary target for brain_map diagnostics.

### Block 5 — Education (c14c_education.txt, 418 files)

Base: `core/c14c_vignettes_e3.pt` (0.990)

| Epoch | Shaped | EN | DE | JP | ZH | Notes |
|---|---|---|---|---|---|---|
| E1 | 0.931 | 0.912 | 0.939 | 0.932 | 0.940 | DE/JP/ZH > EN — vignette rotation effect still active. EN floor 0.83 on causal Q: (garbled EN+JP+DE). |
| E2 | **0.933** | **0.949** | 0.938 | 0.914 | 0.932 | Best. EN recovered strongly (+0.037 from E1). JP dropped (−0.018). JP floor 0.79 on '学校は' (garbled CJK). |
| E3 | 0.926 | 0.933 | **0.949** | 0.898 | 0.925 | Regression. JP worst (0.898, floor 0.79 on 4 prompts). DE tied E2 at 0.949. EN floor 0.85 on 'A school is'. |

Best checkpoint: **`core/c14c_education_e2.pt`** (shaped 0.933, EN 0.949)

Key finding: education corpus improved conversational register (question-forming, explanatory completions) but regressed shaped score from vignettes peak (0.990 → 0.933). JP is most fragile to education-register competition. Education diagnostics confirmed the vignettes peak is the performance ceiling for C14c.

---

## Key observations

- **Vignettes breakthrough**: shaped 0.990 at Block 4 E3 — raw ≈ shaped throughout (delta ~0.000), model generates clean text without prompted running-start. ZH 0.998 near-perfect; JP 0.979 weakest (floor 0.94).
- **Education regression**: Block 5 pulls shaped back to 0.933. Conversational Q&A register competes with vignette-style completions. Confirms vignettes E3 as C14c performance ceiling.
- **Multilingual balance at peak**: ZH 0.998 > EN 0.997 > DE 0.985 > JP 0.979 (Block 4 E3). Language rotation eliminated EN/DE positional advantage vs C14a/b.
- **Arithmetic rule confirmed**: standalone arith pass (Block 1, 20 files × 3 epochs) collapsed shaped 0.934 → 0.863. Fixed by prepending arith at 1.6% of grounded block — no bleeding.
- **Brain_map scans**: pending on Block 4 and Block 5 winners (language.jsonl + thinking.jsonl).

---

## C14c winner

| Field | Value |
|---|---|
| Selected checkpoint | `core/c14c_vignettes_e2.pt` |
| Shaped score | 0.989 (EN 0.996, DE 0.983, JP 0.980, ZH 0.997) |
| Rationale | Brain scan overturned the initial shaped-score pick (E3 was 0.001 higher). E3 had spatial after-hub collapse (0.224→0.144, −36%) and lost half its arithmetic_grounded circuit (1,021→528 neurons). E2 preserves spatial coherence and the tightest arithmetic circuits (arithmetic_zh 0.915, arithmetic_jp 0.912 after-hub). |
| Saved to | `checkpoints/c14c_winner.pt` |

### Brain scan summary (E2 vs E3)

| Dimension | E2 | E3 | Better |
|---|---|---|---|
| Language semantic neurons | 2,985 | 3,751 | E3 |
| Grammar dedicated neurons | 814 | 1,212 | E3 |
| Spatial after-hub | **0.224** | 0.144 | **E2** |
| emotions_boundary after-hub | **0.378** | 0.229 | **E2** |
| arithmetic_grounded neurons | **1,021** | 528 | **E2** |
| arithmetic_zh after-hub | **0.915** | 0.869 | **E2** |
| arithmetic_jp after-hub | **0.912** | 0.895 | **E2** |
| arithmetic_de after-hub | 0.623 | **0.758** | E3 |
| rule_application neurons | 635 | **933** | E3 |

Key finding: shaped score (E3 0.990 vs E2 0.989, delta 0.001) was misleading. E3 traded spatial circuit coherence and grounded arithmetic for grammar and rule_application gains. For a model where spatial was already a flagged weakness, that is a structural regression.
