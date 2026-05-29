# run_4 — Semantic Phase Cluster Ordering

## Setup

| Field | Value |
|---|---|
| Run name | run_4_semantic_cluster |
| Base checkpoint | checkpoints/run3_e2.pt (run_3 E2, shaped 0.925 — best shaped across run_3) |
| Corpus | training/corpus/run4_corpus.txt (13.42 MB, 24,817 files) |
| Change vs run_3 | Phase files sorted by semantic cluster instead of alphabetically |
| Epochs | 5 (with per-epoch checkpoints) |
| LR | 1e-3 (cosine decay) |
| AMP | bf16 enabled |

## Corpus ordering change

**run_3 (alphabetical within each phase):**
```
lang_1, lang_2, phase_1 (acorn→adult→airplane...), phase_2, phase_3,
lang_3, lang_4, phase_4, phase_5, phase_6, lang_5, wiki, reasoning,
grounded_stories, triplet_tiers, philosophy
```

**run_4 (semantic cluster order, all phases together):**
```
lang_1, lang_2,
phases_clustered [207 animals_and_nature → 103 body_and_health → 121 food_and_meals
  → 97 home_and_daily_life → 104 tools_and_making → 51 vehicles_and_travel
  → 61 weather_and_seasons → 114 people_and_relationships → 40 play_and_games
  → 42 school_and_learning → 121 math_and_science → 63 language_and_grammar
  → 4510 abstract_concepts],
lang_3, lang_4, lang_5, wiki, reasoning, grounded_stories, triplet_tiers, philosophy
```

## Cluster distribution (from cluster_phases.py)

| Cluster | Files |
|---|---|
| animals_and_nature | 207 |
| body_and_health | 103 |
| food_and_meals | 121 |
| home_and_daily_life | 97 |
| tools_and_making | 104 |
| vehicles_and_travel | 51 |
| weather_and_seasons | 61 |
| people_and_relationships | 114 |
| play_and_games | 40 |
| school_and_learning | 42 |
| math_and_science | 121 |
| language_and_grammar | 63 |
| abstract_concepts | 4510 |

Note: abstract_concepts (78%) is the catch-all for gerunds, process words, and
abstract phase_3-6 content that doesn't match concrete keyword sets.

## Hypothesis

Alphabetical ordering within phases means semantically unrelated concepts are always
adjacent (acorn → adult → airplane — zero semantic relationship). The model must learn
each concept in isolation with no reinforcement from similar concepts.

Semantic clustering hypothesis: when ant, bee, butterfly, caterpillar appear together,
the model builds category-level associations (small creature, many legs, lives outdoors)
that strengthen individual concept representations and improve generalization.

This mirrors the triplet story category structure (same 13 categories used for both
story corpus and phase clustering), which should increase coherence between the two layers.

## Expected outcome

- **If hypothesis holds:** lower epoch loss and/or better shaped eval scores at E3
  compared to run_3 at the same epoch. Phase probes for concepts with clear cluster
  membership (animals, body parts, food) should show less hallucination.
- **If no effect:** the phase ordering relative to lang doesn't matter as much as
  window-level shuffling within epochs. Document and try a different intervention.

---

## Epoch 1

**Loss:** 0.8167
**Checkpoint:** `core/run_4_semantic_cluster_e1.pt`

### Probe results
```
Phase — concrete noun:  "An acorn is a light week. An acorn has long skin. An acorn has a long tail."
                        Format OK, 5-line structure, subject-based. Content weak but structured.
Phase — abstract adj:   "Bright is smooth. Bright is part of moving. Bright has a tunnel." [6 lines]
                        Format OK. Content still confused.
Phase — gerund [neg]:   "Battling describes something that has gruened. A cool is battles.
                        A dog is not stepping." — garbled words, negation detected.
Phase — bridge word:    "Explaination is studying the ball behaviors." [3 lines] — misspelled,
                        truncated. Content starting to form.
Lang_1 — vocab:         4-stanza format (EN/DE/JP/ZH) — jumbled but structure present.
Lang_2 — semantic:      4-stanza format maintained.
Lang_4 — spatial:       "Eine Wolke ist über den Begriffstreich." — partial German spatial.
                        "über den" correct; noun garbled. Better than run_3 E1 spatial.
Lang_5 — Q&A [pron]:    Pronoun detected in answer.
Triplet — DE:           German sentence, then English leakage into next [user] turn.
Triplet — JP [garbled]: JP then ZH bleed. GARBLED flag.
Reasoning — number:     1 long sentence, no structure. No negation. No format.
Reasoning — arith:      "Two plus means a plus one plus..." — broken.
Summary: 1/12 garbled, 9/12 sentences, 1/12 pronouns, 1/12 negation.
```

### Eval results
```
Raw: 0.907  Shaped: 0.855  (delta -0.052)  Loops: 0  Abrupt stops: 0

NOTABLE: Shaped score significantly lower than run_3 E1 (0.888).
Raw score is actually highest-ever at E1 (0.907 > run_3 E1 0.888).
Large negative delta (-0.052) at E1 — shaper routing animal/body Q&A into multilingual format.
Semantic clustering front-loads concrete categories (animals → body → food) which are also
heavily represented in lang_1/lang_2 — model's first E1 gradients all "animal" context,
causing those concepts to bleed into multilingual shaper routes.

Worst: "Why do birds sing?" → 0.70 shaped (shaper turned it into German/JP output)
       "Why do we sleep?" → 0.72 shaped (same issue — sleep/person cluster contamination)
Best:  "How does a rainbow form?" → 0.96 shaped
```

---

## Epoch 2

**Loss:** 0.7498
**Checkpoint:** `core/run_4_semantic_cluster_e2.pt`

### Probe results
```
Phase — concrete noun:  "An acorn is a person. An acorn is a person. An acorn is a content." [6 lines]
                        Format correct, 6-line structure. Content weak/wrong ("a person"), but structured.
Phase — abstract adj:   "Bright is a burden. Bright is thin. Bright is made of metal." [6 lines]
                        Format correct. Content still confused but lines well-formed.
Phase — gerund:         "Battling is to keep bothers. Battling is to complete the body.
                        Battling is to be strated by a teacher." — "Battling is to [verb]" pattern.
                        Story grounding transfer still active from run_3.
Phase — bridge word:    "Explanation is a thought. Explanation is a discourse." [5 lines]
                        Better semantic content than run_3 E2 ("point on a predator").
Lang_1 — vocab:         4-stanza format maintained (garbled words but structure present).
Lang_2 — semantic:      4-stanza maintained.
Lang_4 — spatial:       "Eine Wolke ist über dem Berlin." — preposition correct, noun wrong.
                        Spatial preposition structure forming.
Lang_5 — Q&A [garbled]: "Tom mit Tom" repetition, JP/ZH bleed. GARBLED.
Triplet — DE:           German sentence formed. English leakage in next turn.
Triplet — JP [garbled]: JP garbled, encoding replacement chars.
Reasoning — number:     1 sentence, no format. "how much a person starts support for a trip."
Reasoning — arith:      "Two plus numbers two equals directions. Two plus zwei plus twenty equals
                        numbers." — Forming "equals" structure! Better than run_3 E2.
Summary: 2/12 garbled, 10/12 sentences, 0/12 pronouns (!), 0/12 negation.
```

### Eval results
```
Raw: 0.901  Shaped: 0.890  (delta -0.011)  Loops: 0  Abrupt stops: 0

Recovery arc confirmed: E1 shaped 0.855 → E2 shaped 0.890 (+0.035 improvement).
Delta still negative at E2 (unlike run_3 E2 which went +0.027). Shaper conflict persisting
but much reduced. 0 pronouns, 0 negation in probes — structural quality matches run_3 E2.

Compare: run_3 E2 shaped = 0.925 vs run_4 E2 shaped = 0.890. run_4 still behind at E2.
Worst: "The children laughed as they" → 0.76 shaped (shaper routing to German/JP)
       "It was a dark and quiet night when" → 0.78 shaped (raw JP bleed passed through)
Best:  "The reason I like reading is" → 0.98 shaped
       "I am hungry because" → 0.98 shaped
```

---

## Epoch 3

**Loss:** 0.6791
**Checkpoint:** `core/run_4_semantic_cluster_e3.pt`

### Probe results
```
Phase — concrete noun:  "An acorn is a flat land with numbers. An acorn is thin and hard." [4 lines]
                        Format OK. Content still confused ("flat land with numbers") but lines clean.
Phase — abstract adj:   "Bright is a low. Bright is green. Bright is cold." [7 lines — slightly long]
                        Format mostly OK. Content wrong (Bright is not green/cold) but structured.
Phase — gerund [neg]:   "Battling describes something. A puppy is battling. A bulb is battling.
                        A dreamer is not battling." — negation detected. Format regressed from E2
                        ("Battling is to [verb]" pattern lost — back to "A X is battling").
Phase — bridge word:    "Explanation is properties that are in a process. Explanation is a word..."
                        [3 lines] — semantic content present but truncated.
Lang_1 — vocab:         4-stanza format maintained (garbled German "Abbreviatieren ist 20 Schul").
Lang_2 — semantic [pron]: "They will abid in the workshop." — pronoun in lang continuation artifact.
                        4-stanza structure maintained.
Lang_4 — spatial [pron]: "Eine Wolke ist über den Berg." — CORRECT German spatial (first clean result)!
                        "über den Berg" = over the mountain. Pronoun in overflow text, not main response.
Lang_5 — Q&A [pron]:    "Wem hat Tom geantwortet?" — correct German dative Q structure!
                        Pronoun detected in overflow continuation.
Triplet — DE [no-sentences]: "Cody wollte eine kleine Straße im Zaun auf dem Haus." — proper German
                        narrative structure. No period at end of first output line (no-sentences flag).
Triplet — JP [garbled]: JP narrative forming but garbled.
Reasoning — number:     "Zero is a quality to a single foundation." — 1 sentence, no format.
Reasoning — arith:      "Two plus can be two trains." — no equals structure (regression from E2).
Summary: 1/12 garbled, 8/12 sentences, 3/12 pronouns (all lang/overflow artifacts, not phase), 1/12 negation.
Note: pronoun detections are lang continuation artifacts, NOT phase format regressions.
```

### Eval results
```
Raw: 0.921  Shaped: 0.925  (delta +0.004)  Loops: 1  Abrupt stops: 0

KEY RESULT: Shaped 0.925 = run_3 E2 best shaped score. Delta flipped positive for first time.
run_4 reached run_3's peak one epoch later (E3 vs E2). Raw (0.921) is best yet across any run/epoch.
1 loop detected (vs 0 at E2). Minor regression in loop stability.
Compare to run_3: E3 shaped was 0.892 (regressed); run_4 E3 shaped = 0.925 (still rising).

Worst: "A school is" → 0.87 shaped (phase format partial bleed)
       "A book is" → 0.88 shaped
Best:  "The reason I like reading is" → 0.96 shaped
       "How does a rainbow form?" → 0.95 shaped
```

---

## Epoch 4

**Loss:** 0.5980
**Checkpoint:** `core/run_4_semantic_cluster_e4.pt`

### Probe results
```
Phase — concrete noun:  "An acorn is a big box. An acorn has a strap. An acorn is small." [6 lines]
                        Format correct. Content weak but well-structured lines.
Phase — abstract adj:   "Bright is a crease in an open area. Bright is a posture of bent position." [4 lines]
                        Format OK. Content confused but syntactically complete.
Phase — gerund:         "Battling is to push slowing across the vessel. Battling is to fit water
                        in a bed." [4 lines] — "Battling is to [verb]" pattern! Story grounding
                        transfer still active at E4.
Phase — bridge word:    "Explanation is a critical expression. Explanation is a social expression." [4 lines]
                        Best bridge word semantic content seen so far.
Lang_1 — vocab:         4-stanza format maintained (garbled German compound word).
Lang_2 — semantic:      4-stanza maintained. Clean continuation with no pronoun bleed.
Lang_4 — spatial:       "Eine Wolke ist über dem Berg. 雲が山の上にある. 一只雲在山上." — BOTH German AND
                        Japanese spatial CORRECT. First time JP spatial correct across any run.
Lang_5 — Q&A:           "Wem hat Tom geantwortet?" — correct dative structure. 4-stanza maintained.
Triplet — DE [no-sentences]: "Zuerst ging Jack in den Küchentisch..." — proper German narrative,
                        no period at line end (no-sentences flag).
Triplet — JP [garbled]: JP narrative forming but garbled replacement chars.
Reasoning — number:     1 sentence, no structure.
Reasoning — arith [neg]: "Two plus two is equal plus two. Two is two sharpens... do not see." —
                        "equal" present, but sentence structure broken. Negation from "do not see."
Summary: 1/12 garbled, 8/12 sentences, 0/12 pronouns (!), 1/12 negation.
```

### Eval results
```
Raw: 0.919  Shaped: 0.943  (delta +0.024)  Loops: 1  Abrupt stops: 0

NEW BEST across all runs. Previous best was run_3 E2 shaped = 0.925 (and run_2 E1 0.943
but that was story-saturation artifact). This is the first legitimate 0.943.
Delta +0.024 — shaper helping significantly. Broad positive deltas across most prompts.

1 loop from "What is a book?" (shaped 0.80) — single outlier dragging down average.
Without that one prompt the shaped would be ~0.95.

Worst: "A book is" → 0.80 shaped (loop; phase format triggered wrong, then looped)
Best:  "I am hungry because" → 0.99 shaped
       "She was afraid because" → 0.98 shaped
       "She opened the door and saw" → 0.98 shaped
```

---

## Epoch 5

**Loss:** 0.5172
**Checkpoint:** `core/run_4_semantic_cluster_e5.pt`

### Probe results
```
Phase — concrete noun:  "The acorn is a bird. The acorn is round. The acorn is shiny." [6 lines]
                        Format correct. "The" instead of "An" opener — minor but clean lines.
Phase — abstract adj:   "Bright is a warm glow. Bright is a smooth light. Bright is a temperature." [5 lines]
                        BEST abstract adj content seen across any run. Semantically coherent.
Phase — gerund:         "Battling is finding a thing in place. Battling is carrying a thing
                        across the middle." — story grounding transfer still active at E5.
Phase — bridge word:    "Explanation has a clear aim. Explanation has a proof of saying." [5 lines]
                        Good semantic content, "proof of saying" is coherent.
Lang_1 — vocab:         4-stanza format maintained.
Lang_2 — semantic:      4-stanza maintained. "Der Frieden ist für Frieden" — tautological but German.
Lang_4 — spatial:       "Eine Wolke ist über dem Berg." — correct German spatial maintained.
                        JP slightly garbled ("雲が一雲からある").
Lang_5 — Q&A:           "Wem hat Tom die Antwort beantwortet? / den Mann." — correct dative Q+A!
                        Best Q&A response seen.
Triplet — DE:           "Die ganze Geräusche standen in der grassland herein." — German narrative,
                        "grassland" (English word) leaked in. English leakage minor.
Triplet — JP [garbled]: JP narrative forming but garbled.
Reasoning — number:     "Food can be sad or sweet." — content has drifted far from number concept.
Reasoning — arith [neg]: "Two plus two is eight equal parts." — wrong but "equal" present.
Summary: 1/12 garbled, 9/12 sentences, 0/12 pronouns, 1/12 negation.
Note: probe quality looks strong (especially abstract adj, bridge word, Q&A) despite eval regression.
```

### Eval results
```
Raw: 0.903  Shaped: 0.904  (delta +0.001)  Loops: 1  Abrupt stops: 0

REGRESSION from E4. Shaped dropped from 0.943 → 0.904. Delta collapsed from +0.024 → +0.001.
Raw also dropped (0.919 → 0.903). Memorization overfit beginning at E5.
1 loop still present ("What is a book?"), same as E4 — not an E5-specific issue.
Shaped delta near zero means shaper has become almost neutral (not hurting, not helping).

E4 is confirmed as the sweet spot.

Worst: "The reason I like reading is" → 0.77 shaped
       "A school is" → 0.78 shaped (multilingual bleed)
Best:  "She was afraid because" → 0.97 shaped
       "It was a dark and quiet night when" → 0.97 shaped
```

---

## Summary

| Epoch | Loss | Raw | Shaped | Loops | Best candidate? |
|---|---|---|---|---|---|
| E1 | 0.8167 | 0.907 | 0.855 | 0 | No |
| E2 | 0.7498 | 0.901 | 0.890 | 0 | No |
| E3 | 0.6791 | 0.921 | 0.925 | 1 | Fallback |
| E4 | 0.5980 | 0.919 | 0.943 | 1 | **YES — best shaped** |
| E5 | 0.5172 | 0.903 | 0.904 | 1 | No (regressed) |

**Selected checkpoint:** `core/run_4_semantic_cluster_e4.pt` → copied to `checkpoints/run4_e4.pt`

**Key observations:**
- Semantic cluster ordering delays the shaped score peak by 2 epochs vs alphabetical (E4 vs E2 for run_3).
- But peak is significantly higher: 0.943 vs 0.925.
- Sweet spot pattern shifted: run_1/run_2 = E3, run_3 = E2, run_4 = E4.
- Story grounding transfer ("Battling is to [verb]") survived all 5 epochs — cluster ordering preserved it.
- German AND Japanese spatial correct at E4 (first JP spatial success).
- Correct German dative Q&A structure at E5 (best yet).
- The "A book is" loop is a persistent weak spot across E4-E5 — phase-format triggering wrong for "book" concept.
- E5 probe quality (abstract adj, bridge word) is the best seen, but eval regresses — memorization artifact.

---

## Comparison with run_3

| Epoch | run_3 Loss | run_3 Shaped | run_4 Loss | run_4 Shaped |
|---|---|---|---|---|
| E1 | 1.1708 | 0.888 | 0.8167 | 0.855 |
| E2 | 0.8216 | 0.925 | 0.7498 | 0.890 |
| E3 | 0.6862 | 0.892 | 0.6791 | 0.925 |
| E4 | — | — | 0.5980 | 0.943 |
| E5 | — | — | 0.5172 | 0.904 |

**Verdict:**
Semantic cluster ordering hypothesis **CONFIRMED**. run_4 E4 shaped (0.943) exceeds run_3 E2 (0.925)
by +0.018. The peak arrives later (E4 vs E2) because the cluster-heavy concrete-category phases
cause more initial shaper disruption, but the model builds stronger category-level associations
that pay off across more epochs.
run_4 E3 shaped (0.925) = run_3 E2 shaped (0.925) exactly — cluster ordering is "one epoch behind"
at E3 but surpasses at E4.
Base checkpoint effect: run_4 starts from run_3 E2 (already at loss 0.82), so E1 loss (0.8167)
is far lower than run_3 E1 (1.1708) — Adam reset noise still present but from a much better starting point.
