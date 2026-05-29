# run_8 — Arithmetic State-Change Stories

## Setup

| Field | Value |
|---|---|
| Run name | run_8_arithmetic_stories |
| Base checkpoint | checkpoints/run7_e1.pt (run_7 E1, shaped 0.924 — format transfer confirmed) |
| Corpus | training/corpus/run8_corpus.txt (13.49 MB, 24,901 files) |
| Change vs run_7 | +72 new grounded stories (stories 31–48 × 4 languages) in training_data/grounded_stories/ |
| Intervention type | `grounded_story_arithmetic` (new story type; state-change schema) |
| Epochs | 5 |
| LR | 1e-3 (cosine decay) |
| AMP | bf16 enabled |

## Motivation

Run_7 confirmed arithmetic format transfer: the model now produces "Two plus two is..."
consistently at E2. The specific answer ("four") did not stabilise within 3 epochs.
Two failure modes identified:

1. **"equals" vs "is" tension** — existing reasoning files use "equals"; run_7 drill files
   use "is". Two competing completions for the same prefix prevented the answer from locking in.

2. **Single retrieval pathway** — drill files train only the direct Q&A format. The fact
   "four" was not grounded in any other context.

Run_8 addresses both:
- 18 arithmetic state-change stories (×4 languages) ground the facts through concrete world
  events using the goal→state→transition→acquisition→merge→verification schema.
- Story 47 (school lesson) explicitly bridges "is" and "equals" as equivalent forms for the
  same fact ("See? It's the same.") — resolving the tension by teaching synonymy rather than
  choosing one form.
- Story 48 introduces Bello (1+1=2) — arithmetic grounded in a real world event.
- Paraphrase variants appear in every story (character states "equals", second character
  counts aloud and says "is" or "makes") — multiple surface forms converging on one fact.

Hypothesis: grounding "four" through narrative world events (Emma counts, Taro calculates,
Gran verifies) will anchor the answer across retrieval contexts. The school lesson story
teaches the "equals"/"is" equivalence directly, removing the competing-completion failure mode.

---

## Epoch 1

**Loss:** 0.7229
**Checkpoint:** `core/run_8_arithmetic_stories_e1.pt`

### Probe results
```
Phase concrete noun:  "An acorn is round. An acorn is made of fruit." — 5 lines, sentences OK; content noisy
Phase abstract adj:   "Bright is a thing. Bright is outdoor. Bright is hot." — 6 lines, sentences OK
Phase gerund:         "Battling describes the same way so often change." — 2 lines; garbled content [flag]
Phase bridge word:    "Explanation is defeats. Explanation is a behavior." — 5 lines, OK
Lang_1 vocab:          5-stanza visible, sentences OK
Lang_2 semantic:       DE/JP/ZH stanza present; content mixed
Lang_4 spatial:        "über dem Boden" — dative correct, wrong noun (Boden=ground not Berg)
Lang_5 Q&A:            "geantwortet? トムはどこで答えた？" — structure present, JP/ZH partial
Triplet DE:            1 line, no-sentences [flag]
Triplet JP:            Garbled [persistent flag]
Reasoning number:      "Zero is the speech of what the seems curious yet." — 1 line, confused [flag]
Reasoning arithmetic:  "Two plus two is two." — PREFIX CORRECT; answer echoes subject (same as run_7 E1)

Summary: 1/12 garbled, 9/12 sentences, 0/12 pronouns, 1/12 negation
Arithmetic: prefix stable; answer "two" — echo of subject, not retrieved fact
```

### Eval results
```
Raw:    0.891
Shaped: 0.901   delta: +0.010 (positive shaper delta)
Loops:  0
Abrupt: 0

Worst:  "Why do we sleep?"         → 0.73 shaped (DE/JP bleed in shaper)
        "A book is"                → 0.80 shaped
Best:   "My favourite memory is"   → 0.98 shaped
        "The reason I like reading" → 0.95 shaped

vs run_7 E1 base: -0.023 below (0.901 vs 0.924) — E1 warmup regression expected
```

---

## Epoch 2

**Loss:** 0.6818
**Checkpoint:** `core/run_8_arithmetic_stories_e2.pt`

### Probe results
```
Phase concrete noun:  "An acorn is big. An acorn has sound." — 6 lines, sentences OK
Phase abstract adj:   "Bright is slicing. Bright is shony. Bright is showly." — 7 lines; neologisms but structured
Phase gerund:         "Battling describes something." — 3 lines; negation present [flag]
Phase bridge word:    "Explanation is a concept. Explanation is a special object." — 5 lines, clean
Lang_1 vocab:          4-stanza visible, sentences OK
Lang_2 semantic:       DE/JP/ZH stanza present
Lang_4 spatial:        "der Berge" — case drift (genitive? ungrammatical locative); regression from E1
Lang_5 Q&A:            "geantwortet? トムはいつ答えた？" — structure present, JP drift
Triplet DE:            1 line, no-sentences [flag]
Triplet JP:            Garbled [persistent]
Reasoning number:      "Zero means one of an equal result in a box." — 1 line, confused [flag]
Reasoning arithmetic:  "Two plus two is two." — prefix correct; still echoing subject

Summary: 1/12 garbled, 9/12 sentences, 0/12 pronouns, 1/12 negation
Arithmetic: no change from E1 — answer still "two"
```

### Eval results
```
Raw:    0.910
Shaped: 0.906   delta: -0.004
Loops:  3       ("What is a friend?", "The old man walked slowly because", one other)
Abrupt: 0

Worst:  "The old man walked slowly because"  → 0.76 shaped (story bleed: "he wanted a reed ball")
        "The best thing about summer is"     → 0.80 shaped
Best:   "I am hungry because"               → 0.98 shaped
        "The reason I like reading is"      → 0.97 shaped

vs E1:  shaped +0.005; loops 0→3 — highest shaped but loop count rising
vs run_7 E1 base: -0.018 below (0.906 vs 0.924)
```

---

## Epoch 3

**Loss:** 0.6222
**Checkpoint:** `core/run_8_arithmetic_stories_e3.pt`

### Probe results
```
Phase concrete noun:  "An acorn is cloudy. An acorn is smooth." — 6 lines, sentences OK
Phase abstract adj:   "Bright is a practical instruction of something." — 3 lines, abstract OK
Phase gerund:         "Battling describes something. A map is battling." — 3 lines, OK
Phase bridge word:    "Explainable is a fact of accuracy." — 5 lines; opener drift ("Explainable" not "Explanation")
Lang_1 vocab:          3-stanza, sentences OK
Lang_2 semantic:       DE/JP/ZH stanza present; "still" (German: still) correct register
Lang_4 spatial:        "über dem Berg." — DATIVE CORRECT; JP "雲が一本山の上にある" correct; ZH "一条雲在山上" correct
Lang_5 Q&A:            "geantwortet? トムは誰を答えた？ 湯姆答就思考了誰？" — trilingual structure
Triplet DE:            1 line, no-sentences [flag]
Triplet JP:            Garbled [persistent]
Reasoning number:      "Zero is a quantity of division. The teacher orders..." — 1 line; "teacher" echo from story 47 [note]
Reasoning arithmetic:  "Two plus two is five." — PREFIX CORRECT; WRONG ANSWER — new wrong number [regression flag]
                        "Two and two and two make five." — suggests 2+3=5 story bleed into arithmetic probe

Summary: 1/12 garbled, 9/12 sentences, 0/12 pronouns, 0/12 negation — cleanest probe flags
Arithmetic: answer changed to "five" — evidence of 2+3=5 story content bleeding into probe register
Spatial: über dem Berg CORRECT — dative stable; best spatial result so far in run_8
```

### Eval results
```
Raw:    0.908
Shaped: 0.902   delta: -0.006
Loops:  1       ("A book is")
Abrupt: 0

Worst:  "A school is"        → 0.79 shaped
        "Why do we sleep?"   → 0.82 shaped
        "Why do birds sing?" → 0.83 shaped
Best:   "She was afraid because"         → 0.98 shaped
        "The reason I like reading is"   → 0.97 shaped
        "If I could change one thing"    → 0.97 shaped

vs E2:  shaped -0.004; loops 3→1 — cleaner than E2; probe flags cleanest of run
```

---

## Epoch 4

**Loss:** 0.5448
**Checkpoint:** `core/run_8_arithmetic_stories_e4.pt`

### Probe results
```
Phase concrete noun:  "An acorn has a si□nk. An acorn has a hammer." — 6 lines; content noisy; 1 garbled char
Phase abstract adj:   "Bright is the sun. Bright is a warm spot." — 6 lines, sentences OK; content grounded [note]
Phase gerund:         "Battling is a careful motion. Battling is a heartbeat of a motion." — 4 lines, OK
Phase bridge word:    "Explanation is a general promise in written language." — 3 lines, abstract OK
Lang_1 vocab:          5-stanza visible, sentences OK
Lang_2 semantic:       DE/JP/ZH stanza present
Lang_4 spatial:        "über dem Berg." — DATIVE CORRECT; JP "雲が山の上にある" correct; ZH "一条云在山上" correct
Lang_5 Q&A:            "geantwortet? トムは誰を告げた？ 湯姆密别了誰？" — structure present; JP verb drift
Triplet DE:            3 lines, sentences OK [improvement]
Triplet JP:            Garbled [persistent]
Reasoning number:      "Zero means three. Four is the sum of zero and zero is the same as zero four." — confused; arithmetic contamination
Reasoning arithmetic:  "A plus two is a number. We write it with the symbol 3." — FORMAT DISRUPTED; pronoun "We"
                        Story character names ("Jack") appearing; narrative frame bleeding into probe

Summary: 1/12 garbled, 10/12 sentences, 1/12 pronouns, 0/12 negation
Arithmetic: format disrupted — story narrative register bleeding into [user]/[Ninereeds] probe
Note: E4 shows overfit signal — do not promote
```

### Eval results
```
Raw:    0.893
Shaped: 0.865   delta: -0.028
Loops:  3       ("A book is", "The old man walked slowly because", one other)
Abrupt: 1       ("Why do birds sing?" → 0.57 shaped)

Worst:  "Why do birds sing?"          → 0.57 shaped (abrupt stop)
        "My favourite memory is"      → 0.71 shaped
        "Why do we sleep?"            → 0.78 shaped
Best:   "She was afraid because"      → 0.98 shaped
        "It was a dark and quiet night" → 0.98 shaped

vs E3:  shaped -0.037; loops 1→3; abrupt 0→1 — clear overfit; do not promote
```

---

## Epoch 5

**Loss:** 0.4631
**Checkpoint:** `core/run_8_arithmetic_stories_e5.pt`

### Probe results
```
Phase concrete noun:  "An acorn is small. An acorn is round. An acorn is bright." — 5 lines, sentences OK; CORRECT
Phase abstract adj:   "Bright is a round move. Bright is a light sound. Bright is a spark." — 6 lines, OK
Phase gerund:         "Battling is a process of completing a target." — 3 lines, OK
Phase bridge word:    "Explanation can happen in a room." — 4 lines; "can happen" format drift
Lang_1 vocab:          6-stanza visible, sentences OK
Lang_2 semantic:       DE/JP/ZH stanza present; "平和は平和だ" (peace is peace) — tautology [note]
Lang_4 spatial:        "über dem Berg." — DATIVE CORRECT; JP "雲の雲は山の上にある" — correct structure, minor noun duplication; ZH "一朵云在山上集落" — correct
Lang_5 Q&A:            "geantwortet? トムは誰に答えを答えた？ 湯姆回答了誰？" — JP redundant but structure present; ZH correct
Triplet DE:            3 lines [improvement]; sentences OK
Triplet JP:            Garbled [persistent]
Reasoning number:      "Zero is a number. We write it with the symbol 8." — pronoun "We"; wrong symbol [flag]
Reasoning arithmetic:  "Two plus two is three." — prefix correct; wrong answer; E3 regression pattern

Summary: 2/12 garbled, 10/12 sentences, 2/12 pronouns, 0/12 negation — late-epoch degradation
Arithmetic: "three" — prefix stable, answer still not "four"; continued regression
```

### Eval results
```
Raw:    0.912
Shaped: 0.905   delta: -0.007
Loops:  1       ("A book is")
Abrupt: 0

Worst:  "A book is"                        → 0.80 shaped (loop)
        "The reason I like reading is"     → 0.81 shaped
        "She opened the door and saw"      → 0.83 shaped
Best:   "I am hungry because"              → 0.98 shaped
        "She was afraid because"           → 0.98 shaped
        "Language is the way people"       → 0.98 shaped

vs E4:  shaped +0.040; loops 3→1; abrupt 1→0 — recovery from E4 overfit
vs E3:  shaped +0.003; pronouns 0→2; garbled 1→2 — marginal shaped gain, worse probe flags
```

---

## Summary

| Epoch | Loss | Raw | Shaped | Loops | Abrupt | Best candidate? |
|---|---|---|---|---|---|---|
| E1 | 0.7229 | 0.891 | 0.901 | 0 | 0 | ✓ cleanest (0 loops, +delta) |
| E2 | 0.6818 | 0.910 | 0.906 | 3 | 0 | ✓ highest shaped; loops concern |
| E3 | 0.6222 | 0.908 | 0.902 | 1 | 0 | ✓ cleanest probe flags (0 pronoun, 0 negation) |
| E4 | 0.5448 | 0.893 | 0.865 | 3 | 1 | ✗ overfit — do not promote |
| E5 | 0.4631 | 0.912 | 0.905 | 1 | 0 | secondary; late-epoch degradation (2 pronouns) |

**Selected checkpoint:** `checkpoints/run8_e2.pt` (E2, shaped 0.906, loops 3)

E2 has the highest shaped score (0.906). Loop count of 3 is below the do-not-promote threshold of 4.
E3 (0.902, 1 loop, cleanest probe flags) is the secondary candidate — preferred base for run_9 if E2
shows instability at inference time.

**Key observations:**
- **Shaped score regression from base.** Run_7 E1 (the base) had shaped 0.924. Best here is 0.906 (E2) —
  a 0.018 regression. The grounded stories did not improve shaped score and may have caused slight regression.
  Plain prose format (no [user]/[Ninereeds] tags) trains a different generation register; the shaper
  penalises register bleed in open-ended prompts.
- **Arithmetic answer never "four" across all 5 epochs.** Different wrong answers: "two" (E1, E2),
  "five" (E3), disrupted (E4), "three" (E5). The prefix "Two plus two is" remains stable from run_7.
  The answer slot is contested — no single completion dominates.
- **E3 "five" is a new signal.** "Two and two and two make five" at E3 suggests the 2+3=5 stories are
  bleeding into the arithmetic probe register. The stories were generated in plain prose, but their
  arithmetic facts are represented in weights and may be competing with the drill file completions.
  This is a different failure mode from the "equals vs is" tension.
- **Dative "über dem Berg" stable from E3 onward** — correct at E3, E4, E5. Best dative consistency
  across any run. The spatial grounding from the German story versions appears to have helped.
- **"The old man walked slowly because" degraded at E2** (0.76 shaped, raw: "he wanted a reed ball") —
  story narrative register bleeding into open-ended prompts. The shaper penalises this.
- **Triplet DE improved at E4/E5** — 3 lines with sentences, up from persistent 1 line. Positive signal.
- **Reasoning number probe shows "teacher" reference at E3** — echo from school lesson story (47).
  Story characters are present in weights.

---

## Comparison with run_7 and run_4 E4

| Epoch | run_4 E4 Shaped | run_7 Shaped | run_8 Shaped |
|---|---|---|---|
| E1 | 0.943 (alltime best) | 0.924 (run_8 base) | 0.901 |
| E2 | — | 0.911 | 0.906 |
| E3 | — | 0.908 | 0.902 |
| E4 | — | — | 0.865 |
| E5 | — | — | 0.905 |

**Success criteria:**
- Arithmetic probe produces "Two plus two is four" or "equals four" at any epoch → **NOT MET**
- Shaped ≥ 0.924 (matches run_7 E1) with loops ≤ 1 → **NOT MET** (best is 0.906 at E2)
- Shaped ≥ 0.943 (beats run_4 E4 baseline) → **NOT MET**

**Failure criteria:**
- No arithmetic breakthrough at any epoch → **MET** — grounded stories insufficient alone
- Shaped < 0.908 (below run_7 peak) at all epochs → **MET** — run did not recover to run_7 peak

**Diagnosis:** The grounded stories delivered new wrong answers (especially "five" at E3 — story bleed
from 2+3=5) rather than anchoring "four". The stories teach arithmetic facts in plain prose register;
the probe operates in [user]/[Ninereeds] register. The two registers are not bridging cleanly.

The school lesson story (47) explicitly taught "is" = "equals" = 2+2=4, but the probe answer never
stabilised at "four". The retrieval problem is deeper than format matching.

**Next intervention — MSM correction (L1-I):**
The failure is narrow and precisely identified: the model produces "Two plus two is [X]" where X is
consistently wrong. The correct answer "four" appears in 12 drill files and story 47 but is losing
to competing completions in the [user]/[Ninereeds] register. A short MSM correction pass (10–15 pairs,
1 epoch, base = run8_e2 or run7_e1) directly targeting the probe answer may resolve what volume-based
approaches have not. The prefix is already locked in — only the answer slot needs anchoring.
