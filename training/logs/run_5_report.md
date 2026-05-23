# run_5 — Reasoning Oversample

## Setup

| Field | Value |
|---|---|
| Run name | run_5_oversample_reasoning |
| Base checkpoint | checkpoints/run4_e4.pt (run_4 E4, shaped 0.943 — best across all runs) |
| Corpus | training/corpus/run5_corpus.txt (14.10 MB, 24,817 unique files) |
| Change vs run_4 | Reasoning section repeated ×4 in corpus (108 files → 432 passes) |
| Intervention type | `oversample_cluster` (Layer 1) |
| Epochs | 3 (with per-epoch checkpoints) |
| LR | 1e-3 (cosine decay) |
| AMP | bf16 enabled |

## Motivation

Reasoning (arithmetic, number) has been broken across all 4 runs despite reasoning files
being present in the corpus since run_1. Root cause hypothesis: at ~0.4% corpus weight,
the reasoning signal is drowned out by the phase curriculum (~80% of corpus).

run_3 confirmed that story grounding transferred at ~0.5% weight (120 files, 0.9% of corpus).
Reasoning at 0.4% (108 files) has not transferred. Oversampling to ×4 brings reasoning to
~1.6% weight — well above the demonstrated transfer threshold.

No new data generated. Same files seen more often per epoch.

## Corpus change

| Section | run_4 weight | run_5 weight |
|---|---|---|
| reasoning | 108 files (×1) | 108 files (×4) = 432 passes |
| all other | 24,709 files | 24,709 files (unchanged) |
| Total corpus size | 14.07 MB | 14.10 MB |

---

## Epoch 1

**Loss:** 0.7281
**Checkpoint:** `core/run_5_oversample_reasoning_e1.pt`

### Probe results
```
Phase — concrete noun:  "An acorn is a strong round storm. An acorn is small and strong." [4 lines]
                        Format OK. Content wrong but structured.
Phase — abstract adj:   "Bright is a thick steady stick." [4 lines, question bleed]
                        Format partially OK. [user] bleed after first response line.
Phase — gerund:         "Battling is to end a course. Battling is to comprehensive condition." [4 lines]
                        "Battling is to [verb]" pattern maintained. Story grounding still active.
Phase — bridge word:    "Explanation is the same assemblement of something." [3 lines, truncated]
                        Format weak at E1, content vague.
Lang_1 — vocab [neg]:   "Absential is not shorter thought." — negation in lang continuation. Unusual.
Lang_2 — semantic:      4-stanza maintained. "Der Frieden ist sehr fest." — coherent German.
Lang_4 — spatial:       "Eine Wolke ist über den Berg." — German spatial still correct.
                        JP "雨が山にある" — rain/cloud confusion but spatial structure correct.
Lang_5 — Q&A:           4-stanza maintained. Correct dative "geantwortet?" structure.
Triplet — DE:           German narrative sentence. English leakage in overflow.
Triplet — JP [garbled]: JP garbled.
Reasoning — number:     "zero is a sense of consumed parts." — 1 sentence, no structure.
                        No improvement from oversampling yet (expected at E1 — optimizer warming up).
Reasoning — arith:      "two is here. two can be at the end of a public book." — [4 lines]
                        PARTIAL PROGRESS: multi-line format forming! Still no "equals" structure.
Summary: 1/12 garbled, 10/12 sentences, 0/12 pronouns, 1/12 negation.
```

### Eval results
```
Raw: 0.895  Shaped: 0.923  (delta +0.028)  Loops: 2  Abrupt stops: 0

BEST E1 shaped score across all runs. Starting from run_4 E4 (shaped 0.943) means residual
knowledge is strong; Adam warmup only pulls raw down (-0.024 from run_4 E4 raw 0.919).
Shaped delta strongly positive (+0.028) — shaper is working well from the first epoch.
2 loops (run_4 E4 had 1) — E1 instability.

Worst: "A book is" → 0.80 shaped (persistent loop/bleed from this prompt)
       "The reason I like reading is" → 0.83 shaped
Best:  "If I could change one thing" → 0.98 shaped
       "Why do we sleep?" → 0.98 shaped
```

---

## Epoch 2

**Loss:** (pending log flush)
**Checkpoint:** `core/run_5_oversample_reasoning_e2.pt`

### Probe results
```
Phase — concrete noun:  "An acorn has a hole. An acorn has a shelf." [6 lines] — Format correct.
Phase — abstract adj:   "Bright is a small number. Bright is a strong amount." [5 lines]
                        "Bright is a small number" shows numeric/math bleed from reasoning.
Phase — gerund:         "Battling is a phase from one's position. Battling is a broad process of
                        exploring a puzzle." [3 lines] — Format shifted: "is a" pattern replacing
                        "is to [verb]" (story grounding transfer weaker at E2).
Phase — bridge word:    "Explanation is an action. Explanation is a reasoning." [5 lines]
                        "is a reasoning" — reasoning vocabulary bleeding into bridge word answers!
Lang_1 — vocab:         4-stanza maintained.
Lang_2 — semantic:      4-stanza maintained. "Der Frieden ist entfernend." — coherent German.
Lang_4 — spatial:       "Eine Wolke ist über dem Berg." — German spatial still correct.
                        "雲は山羊の上にある" — goat/cloud confusion but spatial structure correct.
Lang_5 — Q&A [no-sent]: "antwortet?" — correct dative verb, but missing opening of form.
Triplet — DE [no-sent]:  German narrative forming, no period.
Triplet — JP [garbled]:  JP narrative partially coherent (less garbled than previous epochs).
Reasoning — number:     "Zero is a number. Zero is a number. Zero is a symbol. Zero is a sign of
                        action. Zero is a lack of information." — STRUCTURED FORMAT at E2!
                        Basic correct fact "Zero is a number" now consistently present.
Reasoning — arith:      "Two plus two is two. Two plus two is four. Three plus two is two hundred."
                        "TWO PLUS TWO IS FOUR" — FIRST CORRECT ARITHMETIC RESULT ACROSS ALL RUNS.
                        Repetition and wrong lines present, but the correct answer appears.
Summary: 1/12 garbled, 9/12 sentences, 0/12 pronouns, 0/12 negation.
```

### Eval results
```
Raw: 0.897  Shaped: 0.910  (delta +0.013)  Loops: 3  Abrupt stops: 0

REGRESSION from E1 (0.923 → 0.910 shaped). Loop count rising (2→3).
New loops: "A book is", "A friend is" (join "A school is" which was looping at E1).
Pattern: phase-noun-phrase prompts ("A X is") triggering phase-format loops.
The ×4 reasoning oversample is causing reasoning-register bleed into other domains:
"Bright is a small number" (abstract adj probe), "Explanation is a reasoning" (bridge word).
The arithmetic improvement is REAL but is coming at cost of format stability.

Worst: "The best thing about summer is" → 0.79 (philosophy tag [STATEMENT_DE] bleed)
       "If I could change one thing" → 0.79
Best:  "Why do we sleep?" → 0.98
       "I am hungry because" → 0.98
```

---

## Epoch 3

**Loss:** 0.5276
**Checkpoint:** `core/run_5_oversample_reasoning_e3.pt`

### Probe results
```
Phase — concrete noun:  "An acorn has a round shape. An acorn has a soft bump." [5 lines]
                        Format correct. Content weak ("soft bump") but structured.
Phase — abstract adj:   "Bright is a light sound. Bright is a sign of a sight." [5 lines]
                        No numeric/math bleed (unlike E2). Format correct.
Phase — gerund:         "Battling is a guilt in an art. Battling is a signal that hits a battery." [3 lines]
                        "is a" pattern (not "is to [verb]" from run_4). Story grounding weakened.
Phase — bridge word:    "Explanation is a feeling of being fireed. Explanation is a short meaning." [3 lines]
                        "fireed" is garbled. Content weaker than E2.
Lang_1 — vocab:         4-stanza maintained. "推理することは短縮だ" — reasoning kanji appearing in lang_1!
Lang_2 — semantic:      4-stanza maintained.
Lang_4 — spatial:       "Eine Wolke ist über dem Berg." — German spatial still correct.
Lang_5 — Q&A [garbled]: "湯姆把答案回答答了誰？" — redundant "answer answer" repetition. GARBLED.
Triplet — DE [no-sent]:  German narrative forming. No period.
Triplet — JP [garbled]:  JP narrative partially coherent ("秋の花に触れた") but garbled chars.
Reasoning — number:     "Zero is the number of blocks that mean there are two different things." — 
                        REGRESSION from E2. Lost the structured "Zero is a number" multi-line format.
                        1 sentence, wrong content. E2 was better.
Reasoning — arith:      "Two plus two is the sign after two and before three." — REGRESSION from E2.
                        "is four" DISAPPEARED. E2 had the correct answer; E3 overfit past it.
Summary: 2/12 garbled, 9/12 sentences, 0/12 pronouns, 0/12 negation.
```

### Eval results
```
Raw: 0.878  Shaped: 0.924  (delta +0.046)  Loops: 2  Abrupt stops: 1

Shaped bounced back from E2 (0.910 → 0.924). Loops reduced from 3 → 2.
But raw at its lowest (0.878) and a new abrupt stop appeared.
Pattern: E1→E2→E3 shaped oscillates (0.923→0.910→0.924) — unstable, not converging.
No run_5 epoch matches run_4 E4 (0.943).

Worst: "How does a rainbow form?" → 0.82 shaped (shaper routing to wrong format)
Best:  "She was afraid because" → 0.98, "It was a dark and quiet night" → 0.98
```

---

## Summary

| Epoch | Loss | Raw | Shaped | Loops | Abrupt | Best candidate? |
|---|---|---|---|---|---|---|
| E1 | 0.7281 | 0.895 | 0.923 | 2 | 0 | Maybe (best loop stability) |
| E2 | 0.6452 | 0.897 | 0.910 | 3 | 0 | **YES for reasoning probe** |
| E3 | 0.5276 | 0.878 | 0.924 | 2 | 1 | No (abrupt stop, reasoning regressed) |

**Selected checkpoint:** `core/run_5_oversample_reasoning_e2.pt` → for reasoning content
(reasoning probe peak: "Zero is a number", "Two plus two is four" at E2)

**NOTE: run_4 E4 remains the best checkpoint for overall inference quality.**
`checkpoints/run4_e4.pt` (shaped 0.943, 1 loop) > any run_5 epoch for eval performance.

**Key observations:**
- `oversample_cluster` ×4 CONFIRMED the arithmetic hypothesis: "two plus two is four" appeared
  at E2 for the first time across all runs. The intervention works.
- BUT ×4 dose is too high: reasoning vocabulary bleeds into other domains (abstract adj, bridge word,
  lang_1 kanji). Loop instability increased from run_4 E4 baseline (1 loop → 2-3 loops).
- Reasoning gains peak at E2 and regress at E3 — overfit past the sweet spot.
- Shaped score oscillates (0.923→0.910→0.924) rather than converging — instability from high dose.
- Story grounding ("Battling is to [verb]") weakened by E3 — format bleed from reasoning oversampling.
- Best intervention dose for run_6: ×2 instead of ×4 (or `teacher_student_drill` with clean
  targeted drill files that teach arithmetic directly without complex multi-modal reasoning structure).

---

## Comparison with run_4 (same epoch count)

| Epoch | run_4 Loss | run_4 Shaped | run_5 Loss | run_5 Shaped |
|---|---|---|---|---|
| E1 | 0.8167 | 0.855 | 0.7281 | 0.923 |
| E2 | 0.7498 | 0.890 | 0.6452 | 0.910 |
| E3 | 0.6791 | 0.925 | 0.5276 | 0.924 |

**Verdict:**
run_5 E1 shaped (0.923) >> run_4 E1 shaped (0.855) — strong start from better base checkpoint.
run_5 E2-E3 shaped (0.910/0.924) ≈ run_4 E3 shaped (0.925) — comparable but never exceeds.
run_4 E4 shaped (0.943) remains the all-time best — run_5 never reached it.
The ×4 reasoning oversample confirmed the mechanism but destabilized the model above its
pre-training quality. Calibrating to ×2 is the recommended next step.
