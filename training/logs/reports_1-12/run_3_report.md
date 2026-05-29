# run_3 — Full Interleaved Corpus Training

## Setup

| Field | Value |
|---|---|
| Run name | run_3_interleaved |
| Base checkpoint | checkpoints/run1_e5.pt |
| Corpus | training/corpus/run3_corpus.txt (13.42 MB, 24,817 files) |
| Change vs run_1 | Grounded stories (120 files) interleaved after reasoning, before triplet_tier_1 |
| Change vs run_2 | Stories NOT a separate fine-tune — they are 0.5% of the full corpus |
| Epochs | 3 (with per-epoch checkpoints) |
| LR | 1e-3 (cosine decay) |
| AMP | bf16 enabled |
| Optimizer | AdamW (state reset — weights only loaded from checkpoint) |
| Windows/epoch | 54,959 |
| Steps/epoch | 6,870 |
| Total steps | 20,610 |

## Motivation

run_2 confirmed story grounding transfers to phase-format responses (epoch 3 sweet spot).
But run_2 used a separate fine-tune on 100% story data, causing E1 catastrophic forgetting.

run_3 hypothesis: interleaving stories into the full corpus eliminates format shock.
Stories appear once per epoch scattered through the curriculum, not as a saturating block.

## Initial loss behavior

Step 1: 7.54 → step 25: 3.09 → step 100: 2.53

High initial loss is expected: optimizer state was reset (weights_only=True in load_checkpoint),
so Adam needs to re-accumulate gradient statistics from scratch even though weights are good.
Not the same as E1 catastrophic forgetting from run_2 (which was format disruption).

---

## Epoch 1

**Loss:** 1.1708
**Checkpoint:** `core/run_3_interleaved_e1.pt`

### Probe results

```
Phase — concrete noun:  "An acorn is a way for seeds. An acorn is a piece of behind liquid."
                        Format OK. Content still confused.
Phase — abstract adj:   "Bright is a clear metal. Bright is a decate of the bag."
                        Format OK. Content wrong but structured.
Phase — gerund [neg]:   "Battling describes information. Bathlight is battlenessing."
                        Negation detected. Garbled word forms.
Phase — bridge word:    "Explanation is a stick. Explanation is a service."
                        Format OK. Content vague but not catastrophic.
Lang_1 — vocab:         4-stanza format maintained (EN/DE/JP/ZH).
Lang_2 — semantic frame: 4-stanza format maintained.
Lang_4 — spatial:       4-stanza format maintained.
Lang_5 — Q&A [pron]:    Pronoun detected, but correct dative answer structure.
Triplet — DE:           German response then [user] leakage — minor format bleed.
Triplet — JP [garbled]: Garbled JP characters (UTF-8 replacement chars).
Reasoning — number:     "Zero is a person water" — story-format bleed, 1 pronoun.
Reasoning — arith:      "two is two plus twelve aligns that two territory" — broken.
Summary: 1/12 garbled, 10/12 sentences, 2/12 pronouns, 1/12 negation.
```

### Eval results

```
Raw: 0.888  Shaped: 0.888  (delta 0.000)  Loops: 2  Abrupt stops: 2

Notable: shaped delta = 0.000 — prompt shaper has zero effect at E1.
Model is uniformly confused (contrast: run_2 E1 had shaped > raw = 0.943,
because story format was dominant and the shaper still routed things well).

Worst: "She opened the door and saw" → shapeed 0.65 (JP script mid-response)
Best:  "It was a dark and quiet night when" → 0.98 (story format activated)
```

### Notes

No catastrophic forgetting. Format structure maintained across all probe types.
The optimizer reset (weights_only load) causes Adam to re-adapt, producing uniform
confusion rather than the format-domain collapse seen in run_2 E1.
Story content visible ("the bakery", "he watched the thick new sounds") but mixed
into inappropriate contexts. This is optimizer warmup noise, not format collapse.
Expect sharp recovery at E2.

---

## Epoch 2

**Loss:** 0.8216
**Checkpoint:** `core/run_3_interleaved_e2.pt`

### Probe results

```
Phase — concrete noun:  "An acorn has a large leg. An acorn has a flat shape. [5 lines]"
                        Format fully restored: 5-line structure, subject-based sentences.
Phase — abstract adj:   "Bright is soft. Bright is flat. Bright is thousander." [7 lines]
                        Format correct. Content still weak but structurally right.
Phase — gerund:         "Battling is to practice enough and sound." Format OK.
Phase — bridge word:    "Explanation is a point on a predator. Explanation is an action
                        to conversation." Format OK, content starting to cohere.
Lang_1 — vocab:         4-stanza (EN/DE/JP/ZH) format maintained.
Lang_2 — semantic:      4-stanza maintained.
Lang_4 — spatial:       4-stanza maintained.
Lang_5 — Q&A [garbled]: GARBLED flag — Japanese characters in 4-stanza context.
Triplet — DE:           Coherent German sentence (no-sentences flag = no period, minor).
Triplet — JP [garbled]: Mixed JP+ZH with garbled chars. Still present.
Reasoning — number:     "zero is a strong conductor in size" — story-format bleed, negation.
Reasoning — arith:      "Two plus twelve is two opposite on a road" — still broken.
Summary: 2/12 garbled, 8/12 sentences, 0/12 pronouns (!), 2/12 negation.
```

### Eval results

```
Raw: 0.898  Shaped: 0.925  (delta +0.027)  Loops: 0  Abrupt stops: 0

Strong recovery from E1. Shaped delta back to +0.027 (shaper working again).
0 loops, 0 abrupt stops — format stability restored.

Best: "Why do we sleep?" → 0.98 shaped (huge +0.274 delta)
Worst: "A book is" → 0.79 shaped (phase format triggered with wrong content)
```

### Notes

Pronoun count dropped to zero (0/12) — strong signal. Format structure fully restored.
Content accuracy still poor (acorn "has a large leg"), but all structural markers present.
Recovery arc confirmed: E1 confusion → E2 format restoration → expecting E3 semantic content.
Loss curve (1.17 → 0.82) mirrors run_2 arc (1.27 → 0.84).

---

## Epoch 3

**Loss:** 0.6862

**Checkpoint:** `core/run_3_interleaved_e3.pt`

### Probe results

```
Phase — concrete noun:  "An acorn is a colorful beam or tall. An acorn has holes in a soft board."
                        Format correct, 4-line structure. Content still weak but structured.
Phase — abstract adj:   Format OK. Content vague.
Phase — gerund:         "Battling is to explain a real payment. Battling is to put a set of
                        internal mistakes." — "Battling is to [verb]" pattern confirmed.
                        STORY GROUNDING TRANSFER confirmed for run_3.
Phase — bridge word:    "Explanation is a bright belief." — more coherent than E1/E2.
Lang_1 — vocab:         4-stanza (EN/DE/JP/ZH) format maintained.
Lang_2 — semantic:      4-stanza maintained.
Lang_4 — spatial:       "Eine Wolke ist über den Bergen." — CORRECT German spatial construction.
                        First clean spatial probe result across all runs.
Lang_5 — Q&A:           Format maintained.
Triplet — DE:           Full German narrative sentence, no English leakage.
Triplet — JP:           Japanese sentence, less garbled than E1/E2.
Reasoning — number:     Still broken. Reasoning structure not consolidated at E3.
Reasoning — arith:      Still broken.
Summary: 0/12 pronouns, 0/12 negation — cleanest probe result across all run_3 epochs.
```

### Eval results

```
Raw: 0.906  Shaped: 0.892  (delta -0.014)  Loops: 1  Abrupt stops: 0

NOTABLE: shaped delta went NEGATIVE at E3 (was +0.027 at E2).
Raw score improved (0.906 > 0.898) but shaped score dropped (0.892 < 0.925).
The prompt shaper is slightly hurting E3 — model has learned patterns the shaper penalizes.

Worst: "Language is the way people" → 0.78 shaped (-0.170 delta — shaper made it significantly worse)
       "If I could change one thing, I would" → raw content had [USER_DE] philosophy tags bleeding in
Best:  "Why do we sleep?" → 0.98 shaped
```

### Notes

E3 confirms story grounding transfer ("Battling is to [verb]" pattern) and the first correct
German spatial construction seen across all runs. Probes are the cleanest yet: 0 pronouns, 0 negation.

However, shaped score *dropped* at E3 (0.892 vs E2's 0.925). Raw improved slightly.
The negative shaper delta suggests the model has picked up some content patterns (philosophy tags
leaking into open-ended prompts, unusual phrasing) that the shaper penalizes. E2 is the
stronger practical checkpoint despite E3's better probe scores.

Loss curve (1.17→0.82→0.69) is clean but shallower than run_2 (1.27→0.84→0.54),
consistent with a fuller, more diverse corpus rather than story-saturated fine-tuning.

---

## Summary

| Epoch | Loss | Raw | Shaped | Loops | Best checkpoint? |
|---|---|---|---|---|---|
| E1 | 1.1708 | 0.888 | 0.888 | 2 | No |
| E2 | 0.8216 | 0.898 | 0.925 | 0 | **YES — best shaped** |
| E3 | 0.6862 | 0.906 | 0.892 | 1 | No (shaped regresses) |

**Selected checkpoint:** `core/run_3_interleaved_e2.pt` → copied to `checkpoints/run3_e2.pt`

**Key observations:**
- No catastrophic forgetting at E1 — interleaving confirmed as the fix vs run_2.
- Epoch sweet spot is E2 for run_3 (not E3 as in run_1 and run_2).
- Story grounding transfer confirmed at E3 probe level ("Battling is to [verb]").
- E3 raw score is best (0.906) but shaped score regresses — shaper conflict with new content patterns.
- First correct German spatial construction at E3 ("Eine Wolke ist über den Bergen").
- Philosophy tag leakage suspected at E3 (open-ended prompts triggering [USER_DE] format).

---

## Comparison with run_2 (same epochs)

| Epoch | run_2 Loss | run_2 Shaped | run_3 Loss | run_3 Shaped |
|---|---|---|---|---|
| E1 | 1.2690 | 0.943 | 1.1708 | 0.888 |
| E2 | 0.8427 | 0.928 | 0.8216 | 0.925 |
| E3 | 0.5384 | 0.922 | 0.6862 | 0.892 |

**Verdict:**
run_2 shaped scores are more stable across epochs (0.943→0.928→0.922, very flat).
run_3 shows sharper recovery arc but shaped score peaks at E2 then drops.
run_2 was a story-only fine-tune (100% story saturation) — the shaper performed well because
the story format dominated inference. run_3 has richer content (full corpus + stories) which
improves factual probe quality but adds shaper-conflicting content at E3.
No E1 catastrophic forgetting in run_3 (vs run_2 E1 shaped 0.943 which was misleadingly high
due to story-format dominance — see run_2 notes).
**run_3 E2 (0.925 shaped) is comparable to run_2 E2 (0.928) with the advantage of no format collapse risk.**
