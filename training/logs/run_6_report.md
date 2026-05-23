# run_6 — Reasoning Oversample ×2

## Setup

| Field | Value |
|---|---|
| Run name | run_6_oversample_reasoning_x2 |
| Base checkpoint | checkpoints/run4_e4.pt (run_4 E4, shaped 0.943 — best overall) |
| Corpus | training/corpus/run6_corpus.txt (13.65 MB, 24,817 unique files) |
| Change vs run_5 | Reasoning ×2 instead of ×4 (half dose) |
| Change vs run_4 | Reasoning oversampled ×2 on top of base corpus |
| Intervention type | `oversample_cluster` (Layer 1-C) |
| Epochs | 3 (with per-epoch checkpoints) |
| LR | 1e-3 (cosine decay) |
| AMP | bf16 enabled |

## Motivation

run_5 confirmed that `oversample_cluster` on reasoning transfers arithmetic understanding:
"Two plus two is four" appeared at E2 — first correct arithmetic result across all runs.
But ×4 was too aggressive: reasoning vocabulary bled into abstract adj and bridge word
probes, loop count rose from 1 (run_4 E4 baseline) to 3 (run_5 E2), shaped score
peaked at only 0.924 — below run_4 E4's 0.943.

Hypothesis: ×2 provides the arithmetic transfer signal without the cross-domain bleed.
Expected outcome: arithmetic probe improvement at E2 with shaped score ≥ 0.943 and loops ≤ 1.

## Corpus change

| Section | run_5 weight | run_6 weight |
|---|---|---|
| reasoning | 108 files × 4 = 432 passes | 108 files × 2 = 216 passes |
| all other | unchanged | unchanged |
| Total size | 14.10 MB | 13.65 MB |

---

## Epoch 1

**Loss:** 0.7291
**Checkpoint:** `core/run_6_oversample_reasoning_x2_e1.pt`

### Probe results
```
Phase concrete noun:  "An acorn is a curved piece. An acorn is a sharp size." — 5 lines, format OK
Phase abstract adj:   "Bright is moving light on. Bright is direction." — 6 lines, format OK
Phase gerund:         "Battling is removing a space from a scattered place." — 3 lines; "is [verb]ing"
                       pattern (weaker than run_4 "is to [verb]")
Phase bridge word:    "Explanation is sharp. Explanation is made of wood." — 6 lines, content wrong
                       (physical properties bleeding into abstract category)
Lang_1 vocab:          4-stanza-like structure but no DE/JP/ZH stanza (not standard format)
Lang_2 semantic:       4-stanza maintained; "She spoke seamly" — pronoun in continuation [flag]
Lang_4 spatial:        "Eine Wolke ist über den Berg." — German spatial CORRECT
                        JP "雲が窓の上にある" — structure correct (window not mountain, but grammar OK)
Lang_5 Q&A:            4-stanza maintained; "geantwortet?" — correct dative
Triplet DE:            German narrative, no sentence-final period [flag]
Triplet JP:            Garbled [flag]
Reasoning number:      "Zero is a number of seven things that mignores" — broken, 1 sentence [flag]
Reasoning arithmetic:  "Two plus means something opened or large." — no equals structure, 2 lines,
                        negation present [flag]

Summary: 1/12 garbled, 9/12 sentences, 1/12 pronouns, 1/12 negation
Arithmetic probe: no equals structure yet (×2 dose not enough to transfer at E1)
```

### Eval results
```
Raw:    0.912
Shaped: 0.898   delta: -0.014 vs run_4 E4 baseline
Loops:  2       ("A book is" + 1 other)
Abrupt: 0

Worst:  "The children laughed as they"  → 0.66 shaped (DE/JP bleed)
Best:   "My favourite memory is"        → 0.98 shaped
```

---

## Epoch 2

**Loss:** 0.6506
**Checkpoint:** `core/run_6_oversample_reasoning_x2_e2.pt`

### Probe results
```
Phase concrete noun:  "An acorn is a box. An acorn is broken. An acorn is round. An acorn is hard."
                       — 6 lines, format maintained; "is a box" wrong, "is broken" borderline
Phase abstract adj:   "Bright is a small light sound. Bright is a warm light." — 5 lines, OK
Phase gerund:         "Battling describes using a measure with a thing." — 2 lines; still no "is to [verb]"
Phase bridge word:    "Explanation is an action. Explanation is a moment. Explanation is a probability."
                       — 5 lines, abstract content CORRECT (physical property bleed resolved vs E1)
Lang_1 vocab:          4 lines, continuation-style; no DE/JP/ZH stanza
Lang_2 semantic:       DE/JP/ZH stanza visible in continuation
Lang_4 spatial:        "Eine Wolke ist über den Berg. 雲が一つ山にある。一只雷暴在山里。"
                        — German + JP + ZH spatial ALL CORRECT at E2 [improvement vs E1]
Lang_5 Q&A:            "geantwortet? トムは誰に答えた？ 湯姆回答了誰？" — trilingual CORRECT
Triplet DE:            German narrative, no sentence-final period [flag]
Triplet JP:            Garbled [flag — persistent]
Reasoning number:      "Zero is a number. We write it with the symbol 1." — structured but wrong;
                        pronoun "We" present [flag]
Reasoning arithmetic:  "Two plus two is three pieces of two." — HAS "two plus two is" prefix structure
                        but no correct answer; 1 line [×2 dose insufficient for arithmetic transfer at E2]

Summary: 1/12 garbled, 9/12 sentences, 1/12 pronouns, 0/12 negation (improved vs E1)
Arithmetic probe: partial structure ("two plus two is…") but wrong answer — no "equals four"
```

### Eval results
```
Raw:    0.904
Shaped: 0.897   delta: -0.007 (shaper delta)
Loops:  2       ("What is a book?" persistent loop)
Abrupt: 0

Worst:  "How does a rainbow form?"  → 0.78 shaped
        "I am hungry because"       → 0.79 shaped
Best:   "Why do we sleep?"          → 0.98 shaped
        "The reason I like reading" → 0.98 shaped

vs E1:  shaped flat (0.898 → 0.897, -0.001) — no recovery at E2
vs run_4 E4 baseline: -0.046 below (0.897 vs 0.943)
```

---

## Epoch 3

**Loss:** 0.5373
**Checkpoint:** `core/run_6_oversample_reasoning_x2_e3.pt`

### Probe results
```
Phase concrete noun:  "An acorn is a tool. An acorn is broken. An acorn has a door." — 6 lines;
                       format maintained but content degraded (tool, door, handle — wrong properties)
Phase abstract adj:   "Bright is a set of people who will want and change what they think about another."
                       — 1 line, pronoun "they/who", no-sentences [regression from E2]
Phase gerund:         "A step is not battling." — negation present [flag]; 3 lines
Phase bridge word:    "Explanation is a different thing. Explanation is two words or tools in one special way."
                       — 3 lines, abstract content (no physical bleed)
Lang_1 vocab:          4 lines, DE/JP/ZH continuation visible
Lang_2 semantic:       DE/JP/ZH stanza maintained
Lang_4 spatial:        "Eine Wolke ist über dem Berg." — DATIVE CORRECT [spontaneous correction at E3]
                        JP "雲が山になっている" — structure present but content wrong ("is becoming the mountain")
Lang_5 Q&A:            Trilingual maintained; "誰を答えた" — JP accusative を instead of dative に [flag]
Triplet DE:            Sentence structure present; garbled content ("Ein Kind schmelzt auf den Garten")
Triplet JP:            Garbled [flag — persistent]
Reasoning number:      "Zero is a number. We write it with the symbol 20." — pronoun "We", negation
                        ("Zero is not one"), no-sentences [regression]
Reasoning arithmetic:  "Two plus two is two things that make two children last." — prefix structure
                        present but no correct answer; no-sentences [no improvement over E2]

Summary: 1/12 garbled, 8/12 sentences (down from 9), 2/12 pronouns (up from 1), 2/12 negation (up from 0)
Notable: German dative "über dem Berg" appeared spontaneously — correct without MSM
Notable: abstract adj and reasoning probes degraded vs E2 — typical E3 overfit pattern
```

### Eval results
```
Raw:    0.889
Shaped: 0.916   delta: +0.027 (shaper delta)
Loops:  2       ("What is a book?" loop; "What is a friend?" loop)
Abrupt: 0

Worst:  "What is a school?"   → 0.79 shaped (lang bleed in shaper)
        "I am hungry because" → 0.85 shaped
Best:   "Why do we sleep?"    → 0.98 shaped
        "Once upon a time"    → 0.97 shaped

vs E2:  shaped recovered +0.019 (0.897 → 0.916) — positive shaper delta despite raw decline
vs run_4 E4 baseline: -0.027 below (0.916 vs 0.943)
```

---

## Summary

| Epoch | Loss | Raw | Shaped | Loops | Abrupt | Best candidate? |
|---|---|---|---|---|---|---|
| E1 | 0.7291 | 0.912 | 0.898 | 2 | 0 | |
| E2 | 0.6506 | 0.904 | 0.897 | 2 | 0 | |
| E3 | 0.5373 | 0.889 | 0.916 | 2 | 0 | ✓ highest shaped |

**Selected checkpoint:** `checkpoints/run6_e3.pt` (E3, shaped 0.916, loops 2)

**Key observations:**
- ×2 dose did NOT meet success criteria. Shaped peaked at 0.916 — below 0.943 target and below
  run_5 E3 (0.924). No arithmetic breakthrough at any epoch ("Two plus two is four" never appeared).
- Failure criterion met: shaped < 0.925 at all epochs → dose approach to arithmetic transfer via
  `oversample_cluster` is exhausted. ×4 caused bleed; ×2 insufficient. Next: `teacher_student_drill`.
- Loops persisted at 2 throughout — did not recover to run_4 E4 baseline of 1.
- E3 shaped (0.916) recovered from E2 flat despite raw decline (0.904→0.889), indicating the shaper
  is routing better even as raw output quality slightly degrades. Typical late-epoch pattern.
- German dative "über dem Berg" appeared spontaneously at E3 — correct without MSM. The correct
  form was latent; one extra epoch of training pulled it through. MSM not needed for this issue.
- JP garbling and reasoning probes degraded at E3 — standard E3 overfit on richer content.

---

## Comparison with run_5 and run_4 E4

| Epoch | run_4 E4 Shaped | run_5 Shaped | run_6 Shaped |
|---|---|---|---|
| E1 | 0.943 (base) | 0.923 | 0.898 |
| E2 | — | 0.910 | 0.897 |
| E3 | — | 0.924 | 0.916 |

**Success criteria:**
- Shaped ≥ 0.943 at any epoch with loops ≤ 1 → intervention confirmed, run_6 best checkpoint promoted
- Arithmetic probe shows "equals four" at E2 → mechanism transferred at ×2
- No reasoning vocabulary bleed into abstract adj or bridge word probes

**Failure criteria:**
- Shaped < 0.925 at all epochs → ×2 still too high; try ×1 or `teacher_student_drill`
- Loops increase above run_4 E4 baseline (1) → format instability persists; reconsider dose
