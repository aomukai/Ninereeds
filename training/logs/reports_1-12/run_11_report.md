# run_11 — Scaling study 150M (1 epoch)

## Setup

| Field | Value |
|---|---|
| Run name | run_11_150m |
| Base checkpoint | scratch (no resume — fresh initialisation) |
| Corpus | training/corpus/run10_corpus.txt (13.54 MB, 24,937 files) |
| New content | Same as run_10 — 36 counting files (02_counting_*.md) + full corpus |
| Epochs | 1 |
| LR | 1e-3 (cosine decay) |
| AMP | bf16 enabled |
| Model | XL_150M_CONFIG — n_layer=6, n_embd=256, n_head=4, per_layer_weights=True (151.1M actual) |

## Motivation

Part 2 of a three-way scaling study: same corpus (run10_corpus.txt), same procedure (1 epoch, probe + eval), varying model size only.

Run_10 (25M, 1 epoch from run7_e1 base):
- Shaped 0.901 — regression from baseline 0.924
- Arithmetic 0/3 — no correct answers at any epoch
- Hypothesis: 25M may lack the weight space to separate competing completions ("two" from question context vs "four" as answer)

At 150M with per_layer_weights=True, each of 6 Hebbian layers has independent weight matrices. This gives ~6× more associative capacity for the same base dimensions, potentially allowing arithmetic facts to anchor without competing completions overwhelming the answer slot.

Training from scratch because the 25M checkpoint (run7_e1) is architecturally incompatible with the 150M config — tensor shapes do not match.

---

## Epoch 1

**Loss:** 1.1016 (3143.5s / ~52 min)
**Checkpoint:** `core/run_11_150m_e1.pt`

### Probe results
```
Fixed comparison (1/8 pass):
  1+1=2 ✗  "One plus one is one plus one is the same source of constant..."
  2+2=4 ✗  "Two plus two is two. Two and two equals two. Two two three equals two." — format correct, answer echoes question word
  3+1=4 ✗  "Three plus one is three three eyes to eat."
  zero  ✗  Does not say "number"
  dative über ✗  Produces accusative "den Stoff gestiegen"
  acc movement ✓  "den Büro zu einer Spielzeugmaß zu."
  JP autumn ✗  Japanese prompt produces Chinese characters
  ZH autumn ✗  Garbled output

Arithmetic:   0/3 correct  (1+4=5✗  5+3=8✗  1+5=6✗)
              Format present — "Five plus two five is five five." — answer slot echoes question
Dative:       0/3 correct  (produces auf/von/unter instead of über)
Phase format: decent — acorn/bright/explanation have correct structure; battling has negation flag
Garbled:      1/17  (JP triplet)
Pronoun:      1/17
Negation:     1/17 (battling: "A ruler is not battlen")
```

### Eval results
```
RAW:    0.873
SHAPED: 0.913  (delta +0.040 — shaper helps, positive routing)
Loops:  2×  (book, school)
Worst:  'A book is' (0.81 shaped — garbled; persistent from run_4 onward)
        'My favourite memory is' (0.82 shaped)
Best:   'I am hungry because' (0.97)  'If I could change one thing' (0.96)
```

---

## Summary

**Scaling study comparison (1 epoch each):**

| Run | Size | Base | Loss E1 | RAW E1 | Shaped E1 | Arith E1 | Dative E1 | FC E1 |
|---|---|---|---|---|---|---|---|---|
| run_10 | 25.3M | run7_e1 | 0.6613 | 0.913 | 0.901 | 0/3 | 1/3 | — |
| run_11 | 151.1M | scratch | 1.1016 | 0.873 | 0.913 | 0/3 | 0/3 | 1/8 |
| run_12 | 604.2M | scratch | (fill) | (fill) | (fill) | (fill) | (fill) | (fill) |

**Arithmetic retention check:** Did E1 produce correct answers across ≥2/3 random arithmetic probe pairs?

- [ ] Yes → arithmetic capacity confirmed at 150M
- [x] No  → 0/3 correct; answer slot echoes question word ("two plus two is two"); format learned, fact not anchored

**Selected checkpoint:** Not promoted — scratch run, no arithmetic improvement. Retained for scaling comparison.

**Key observations:**
- Shaped 0.913 is notably *higher* than run_10's 0.901 despite scratch init and higher loss. The 150M model routes formats more cleanly — positive shaped delta (+0.040 vs run_10's -0.012).
- Arithmetic failure mode shifted: run_10 produced wrong numbers; run_11 echoes the question word ("two plus two is **two**"). Format is fully present; the answer slot is governed by recency/repetition, not learned facts. Per_layer_weights alone does not fix this.
- Training time barely changed: 52 min (151M) vs 47 min (25M). GPU is not compute-bound on these dimensions — the additional per_layer matrices run efficiently in parallel.
- Implication for run_12: wider embedding (512 vs 256) may provide enough associative separation to anchor the answer slot against question-word repetition. This is the core hypothesis for the next step.
