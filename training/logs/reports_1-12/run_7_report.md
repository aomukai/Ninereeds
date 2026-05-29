# run_7 — Teacher Student Drill: Arithmetic

## Setup

| Field | Value |
|---|---|
| Run name | run_7_teacher_student_drill |
| Base checkpoint | checkpoints/run4_e4.pt (run_4 E4, shaped 0.943 — best overall) |
| Corpus | training/corpus/run7_corpus.txt (13.43 MB, 24,829 files) |
| Change vs run_6 | No oversampling; 12 new arithmetic drill files added to reasoning section |
| Change vs run_4 | Reasoning section: 108 files → 120 files (+12 EN drill files in direct probe format) |
| Intervention type | `teacher_student_drill` (Layer 1-B) |
| Epochs | 3 (with per-epoch checkpoints) |
| LR | 1e-3 (cosine decay) |
| AMP | bf16 enabled |

## Motivation

`oversample_cluster` exhausted for arithmetic transfer: ×4 caused cross-domain bleed (run_5),
×2 was insufficient — no "Two plus two is four" at any epoch (run_6).

Root cause identified: existing reasoning files use "Teach me about..." / multi-modal format
(Symbolic Mode / Verbal Mode / Grounded Story Mode) which does not match the probe output
format. The probe asks "what is two plus two?" and expects "Two plus two is four." — a direct
Q&A pattern not represented in the training data.

12 drill files generated via DeepSeek in exact probe format:
- [user]What is two plus two? → [Ninereeds]Two plus two is four.
- Covers: single-digit addition (×4 files), zero identity (×2), subtraction (×2),
  number identity (×2), equals frame (×1), review (×1)
- 4 Q&A pairs per file, 3–4 lines per response, no pronouns, no negation

Hypothesis: direct format match between training data and probe question will produce
"Two plus two is four" at E2. No oversampling needed — quality of signal over quantity.

## Corpus change

| Section | run_6 | run_7 |
|---|---|---|
| reasoning | 108 files × 2 = 216 passes | 120 files × 1 = 120 passes |
| all other | unchanged | unchanged |
| Total size | 13.65 MB | 13.43 MB |

---

## Epoch 1

**Loss:** 0.7273
**Checkpoint:** `core/run_7_teacher_student_drill_e1.pt`

### Probe results
```
Phase concrete noun:  "An acorn is a long hand thing." — 4 lines, sentences OK; content noisy (E1)
Phase abstract adj:   "Bright is a cold noise. Bright is a warm light." — 5 lines, sentences OK
Phase gerund:         "Battling is the act of moving a thing to do." — 3 lines, OK
Phase bridge word:    "Explanation is for showing. Explanation is for comparing." — 4 lines, OK
Lang_1 vocab:          4-stanza visible; pronoun "it" in continuation [flag]
Lang_2 semantic:       DE/JP/ZH stanza maintained
Lang_4 spatial:        "Eine Wolke ist nötig." — structure lost (E1 warmup regression from run_6 E3 dative)
Lang_5 Q&A:            "zersteht?" — broken German, structure disrupted (E1)
Triplet DE:            1 line, no-sentences [flag]
Triplet JP:            Garbled, no-sentences [persistent flag]
Reasoning number:      "Zero is a quantity of being to be seven." — 3 lines; confused but structured
Reasoning arithmetic:  "Two plus two is two is not two. / Two is not... / Two plus two is not five."
                        — negation storm [E1 warmup noise]; drill signal not yet stabilised

Summary: 1/12 garbled, 10/12 sentences (up from 8), 1/12 pronouns, 1/12 negation
Arithmetic: heavy negation at E1 — expected Adam warmup disruption, not a signal yet
```

### Eval results
```
Raw:    0.882
Shaped: 0.924   delta: +0.042 (shaper delta)
Loops:  1       (down from 2 in all run_6 epochs — positive sign)
Abrupt: 1

Worst:  "The reason I like reading is" → 0.81 shaped
        "She opened the door and saw"  → 0.83 shaped
Best:   "My favourite memory is"       → 0.98 shaped
        "It was a dark and quiet night" → 0.97 shaped

vs run_6 E1:   shaped +0.026 (0.924 vs 0.898) — drill files not causing damage
vs run_6 peak: shaped +0.008 (0.924 vs 0.916) — already above run_6 best at E1
vs baseline:   -0.019 below run_4 E4 (0.943) — closing gap
```

---

## Epoch 2

**Loss:** 0.6502
**Checkpoint:** `core/run_7_teacher_student_drill_e2.pt`

### Probe results
```
Phase concrete noun:  "An acorn has round skin." — 6 lines, sentences OK
Phase abstract adj:   "Bright is a worm of the sky." — 4 lines, sentences OK; content noisy
Phase gerund:         "Battling is to spin in shame." — 4 lines; "is to [verb]" FORMAT RESTORED
Phase bridge word:    "Explanation means a final idea in example or way." — 3 lines, abstract OK
Lang_1 vocab:          5-stanza visible; no pronouns
Lang_2 semantic:       DE/JP/ZH stanza maintained
Lang_4 spatial:        "Eine Wolke ist über dem Bergen." — DATIVE CORRECT [über dem = dative]
                        JP "雲が山の上にある" — CORRECT; both spatial probes passing at E2
Lang_5 Q&A:            "zu andere geantwortet?" — structure present, minor German drift
Triplet DE:            1 line, no-sentences [persistent]
Triplet JP:            Garbled [persistent]
Reasoning number:      "Zero is a number." — CORRECT first line; 6 structured lines; no pronouns
Reasoning arithmetic:  "Two plus two is two." — PREFIX CORRECT but wrong answer; 5 lines;
                        no negation, no pronouns — format locked in, fact not yet resolved

Summary: 1/12 garbled, 10/12 sentences, 0/12 pronouns, 0/12 negation — cleanest probe so far
Arithmetic: format transfer confirmed ("Two plus two is..."); answer wrong ("two" not "four")
Spatial: dative case and JP spatial both correct — drill approach pulling latent forms through
```

### Eval results
```
Raw:    0.909
Shaped: 0.911   delta: +0.002 (shaper delta)
Loops:  1       ("What is a book?" — persistent)
Abrupt: 1

Worst:  "Why do we sleep?"           → 0.81 shaped (DE bleed in shaper)
        "The reason I like reading"  → 0.82 shaped
Best:   "How does a rainbow form?"   → 0.99 shaped
        "She was afraid because"     → 0.98 shaped

vs E1:  shaped -0.013 (0.911 vs 0.924) — normal E2 adjustment from warmup peak
vs run_4 E4 baseline: -0.032 below (0.911 vs 0.943)
```

---

## Epoch 3

**Loss:** 0.5385
**Checkpoint:** `core/run_7_teacher_student_drill_e3.pt`

### Probe results
```
Phase concrete noun:  "An acorn is a hard green tree." — 5 lines, sentences OK
Phase abstract adj:   "Bright is the bright part of a thing." — 3 lines, OK
Phase gerund:         "Battling is following a balloon or shelf." — 3 lines; "is [verb]ing" (not "is to [verb]")
Phase bridge word:    "Explanation is a plan. Explanation is a fact." — 5 lines, clean abstract content
Lang_1 vocab:          5-stanza present, no pronouns
Lang_2 semantic:       DE/JP/ZH stanza maintained
Lang_4 spatial:        "über dem Berg." — DATIVE CORRECT (singular — better than E2 "Bergen")
                        JP "雲が山の上にある" CORRECT; ZH "一条雲在山上" structured — ALL THREE correct
Lang_5 Q&A:            "geantwortet? トムは誰に答えた？ 湯姆回答了誰?" — FULLY TRILINGUAL CORRECT
                        JP uses dative に (correct); complete answer stanza in all four languages
Triplet DE:            1 line, no-sentences [persistent]
Triplet JP:            Garbled [persistent]
Reasoning number:      "Zero is a number." — correct first line; but pronoun "We" and confused body
Reasoning arithmetic:  "Two plus two is the sum of two and two. Two plus two equals three."
                        — structural awareness present but wrong answer ("three"); E3 regression

Summary: 1/12 garbled, 10/12 sentences, 1/12 pronouns, 0/12 negation
Arithmetic: structural awareness ("sum of two and two") but wrong answer — fact not locked in
Spatial: fully correct in all three languages — best spatial probe across all runs
Lang_5: fully trilingual Q&A — best lang_5 probe across all runs
```

### Eval results
```
Raw:    0.893
Shaped: 0.908   delta: +0.015
Loops:  4       (up from 1 — "A book is" + "A friend is" + 2 others; E3 overfit signal)
Abrupt: 1

Worst:  "Why do we sleep?"  → 0.66 shaped (DE/JP bleed)
        "A book is"         → 0.80 shaped (loop)
Best:   "I am hungry because" → 0.98 shaped
        "My favourite memory" → 0.98 shaped

vs E2:  shaped -0.003; loops 1→4 — clear E3 overfit; do not promote
```

---

## Summary

| Epoch | Loss | Raw | Shaped | Loops | Abrupt | Best candidate? |
|---|---|---|---|---|---|---|
| E1 | 0.7273 | 0.882 | 0.924 | 1 | 1 | ✓ highest shaped, lowest loops |
| E2 | 0.6502 | 0.909 | 0.911 | 1 | 1 | cleanest probes (0/12 pronoun, 0/12 negation) |
| E3 | 0.5385 | 0.893 | 0.908 | 4 | 1 | overfit — do not promote |

**Selected checkpoint:** `checkpoints/run7_e1.pt` (E1, shaped 0.924, loops 1)

**Key observations:**
- Arithmetic format transfer confirmed: by E2 the model produces "Two plus two is [answer]" — the
  retrieval frame locked in. But the specific answer ("four") did not stabilise within 3 epochs.
  E3 produced "equals three" — regression. The fact is partially learned, not yet reliable.
- "Equals" vs "is" tension: existing reasoning files use "Two plus two equals four"; drill files
  use "Two plus two is four". Two competing completions for the same prefix may be preventing
  the answer from locking in. Run_8 should unify these forms.
- Lang_4 spatial fully correct at E3 — "über dem Berg" (singular dative), JP, ZH all structured.
  Best spatial performance across all runs. Drill approach stabilised neighbouring knowledge.
- Lang_5 Q&A fully trilingual at E3 — best lang_5 performance across all runs.
- E1 selected despite arithmetic negation noise: shaped 0.924 is the highest and loops=1 is clean.
  E2 (0.911, cleanest probes) is the secondary candidate if E1 shows inference instability.
- Shaped score declining E1→E2→E3 (0.924→0.911→0.908) — run did not beat run_4 E4 (0.943).
  The drill files are not damaging; 12 files at ×1 is a gentle signal that needs more epochs or
  more files to reach the baseline-beating threshold.

---

## Comparison with run_6 and run_4 E4

| Epoch | run_4 E4 Shaped | run_6 Shaped | run_7 Shaped |
|---|---|---|---|
| E1 | 0.943 (base) | 0.898 | 0.924 |
| E2 | — | 0.897 | 0.911 |
| E3 | — | 0.916 | 0.908 |

**Success criteria:**
- Arithmetic probe produces "Two plus two is four" or "equals four" at any epoch → format match confirmed
- Shaped ≥ 0.943 at any epoch with loops ≤ 1 → drill files improve on run_4 E4 baseline
- No cross-domain bleed (reasoning vocab in abstract adj or bridge word probes)

**Failure criteria:**
- No arithmetic breakthrough at any epoch → format mismatch not the root cause; escalate to MSM correction or more drill files
- Shaped < 0.916 (below run_6 peak) at all epochs → drill files caused regression; investigate
