# MSM Cold-Start Phases

This document defines the cold-start MSM curriculum.

Cold-start MSM begins from random weights. Early output may be byte noise, fragments,
loops, malformed words, or semantically wrong sentences. That is expected. A phase may
evaluate only the skill it has explicitly frontloaded.

Each phase must define:

1. **Frontload** - what training examples are allowed, and what is forbidden.
2. **Evaluate** - what probes and metrics measure the phase goal.
3. **Success gates** - what must be true before the next phase can start.

The machine may loop within a phase indefinitely. Failure is evidence for adjusting dose,
data shape, or ordering; it is not a reason to abandon the phase ladder.

Machine-readable phase records must validate against:

`training/pipeline/cold_start_phase_schema.json`

The active phase and canonical phase order are recorded in:

`training/pipeline/msm/state/phase_registry.json`

Phase 0 and Phase 1 are executed by the cold-start block runner, not the later MSM session
loop:

`meta/scripts/msm_phase_runner.py`

The block runner frontloads examples directly into `train.py`, then writes a compact block
report under `training/pipeline/msm/phase_blocks/`. It omits `--resume` when the parent is
`scratch`; no scratch checkpoint file is required.

---

## Phase Rules

- Do not evaluate skills the current or prior phases have not taught.
- Do not treat first exposure as concept failure.
- Do not train from raw wrong answers.
- Checkpoint at small phase boundaries and before risky transitions.
- Review after interference, not wall-clock time.
- Keep historical campaign evidence out of active cold-start parent selection.

---

## Phase 0 - Form Bootstrapping

**Goal:** bounded language-shaped answer-slot control.

Ninereeds is ready for first words when it can produce short printable output in the answer
slot without collapsing into loops or tag noise.

### Frontload

Allowed data shapes:

- copy one visible word
- say one visible word
- complete one tiny sentence
- produce one short template sentence
- answer one mechanical prompt with one word or one short sentence
- stop cleanly after the answer

Example shapes:

```text
[user] say dog
[Ninereeds] dog.

[user] write a short sentence
[Ninereeds] A dog runs.

[user] say red
[Ninereeds] red.
```

Forbidden data shapes:

- facts about concepts
- negation
- multi-turn reasoning
- long completions
- abstract concepts
- multilingual material
- K-8 content

### Evaluate

Probe families:

- answer-slot probes
- word-copy probes
- short-sentence probes
- stop-control probes
- loop/malformed probes

Metrics:

- bounded output rate
- printable text rate
- word-form copy rate
- sentence-shape rate
- speaker-tag corruption rate
- loop/repetition collapse rate
- byte-noise or malformed-fragment rate

Non-goals:

- semantic correctness
- on-topic factual answers
- category knowledge
- chat quality

### Success Gates

Starting defaults, to be tuned empirically:

- bounded output rate >= 0.90
- word-form copy rate >= 0.80
- sentence-shape rate >= 0.70
- speaker-tag corruption rate <= 0.05
- loop/repetition collapse rate <= 0.05
- byte-noise/malformed-fragment rate <= 0.10

Failure interpretation: output-form instability, not concept failure.

---

## Phase 1 - Word Form Introduction

**Goal:** expose the allowlist as stable word forms.

This phase teaches that each allowlist item is a visible word form. It does not teach full
meaning.

### Frontload

Allowed data shapes:

- `say WORD`
- `copy WORD`
- `WORD is a word`
- `the word is WORD`
- tiny one-word and one-sentence answer forms

Forbidden data shapes:

- dense facts
- multi-cluster meanings
- long stories
- grade-school lessons
- philosophical or identity material

### Evaluate

Probe families:

- copy held-out allowlist words
- recognize prompted word form
- answer with the target word in a short response
- avoid drifting into unrelated tags/noise

Metrics:

- exact/near-exact word reproduction rate
- target-word inclusion rate
- bounded output rate
- malformed rate
- off-form drift rate

Non-goals:

- knowing what the word means
- answering factual questions about the word
- producing natural chat

### Success Gates

Starting defaults:

- target-word inclusion rate >= 0.85 on sampled allowlist probes
- exact/near-exact reproduction rate >= 0.75
- bounded output rate >= 0.90
- malformed rate <= 0.10

Failure interpretation: weak form recognition, not failed concept knowledge.

---

## Phase 2 - Basic English Control

**Goal:** crude English question-answer binding.

This phase teaches reusable language machinery before deep concept facts.

### Frontload

Allowed data shapes:

- `X is a word.`
- `X is a thing.`
- `X can be named.`
- simple yes/no forms
- simple `what/who/where` forms
- short one-sentence answers
- explicit non-echo answer-slot drills

Forbidden data shapes:

- large fact bundles
- multi-step reasoning
- K-8 lessons
- free chat

### Evaluate

Probe families:

- yes/no mechanical probes
- `what is WORD?` shallow probes
- non-echo probes
- one-turn and two-turn continuity probes

Metrics:

- answer-slot binding rate
- non-echo rate
- bounded output rate
- simple question-form response rate
- malformed rate

Non-goals:

- deep facts
- rich prose
- broad knowledge

### Success Gates

Starting defaults:

- answer-slot binding rate >= 0.80
- non-echo rate >= 0.75
- simple question-form response rate >= 0.75
- bounded output rate >= 0.90
- malformed rate <= 0.10

Failure interpretation: language-control weakness, not concept failure.

---

## Phase 3 - Concept Grounding

**Goal:** teach word meanings as concept cards.

This is the first phase where concept pass/fail becomes meaningful.

### Frontload

Allowed data shapes:

- category anchors
- properties
- parts
- actions
- uses
- positive anchors
- negative contrasts
- unknown-boundary lines
- controlled practice

Forbidden data shapes:

- broad K-8 lessons before prerequisite concepts pass
- free-practice material as update data
- dense all-in-one corrections

### Evaluate

Probe families:

- category probes
- property/action probes
- same-category contrast probes
- cross-category contrast probes
- unknown-boundary probes
- review-after-interference probes

Metrics:

- original correct rate after prior exposure
- post-correction correct rate
- on-topic rate
- contrast-boundary pass rate
- unknown-boundary pass rate
- protected-anchor status

Non-goals:

- grade-level school knowledge
- long explanatory prose

### Success Gates

Starting defaults:

- target axes pass review after at least one intervening related update
- no off-topic answers in promotion probe
- malformed rate <= configured threshold
- protected anchors pass when tested
- no harmful equivalence persists

Failure interpretation: concept weakness, prerequisite gap, or interference.

---

## Phase 4 - School Curriculum

**Goal:** teach preschool and K-8 knowledge on top of grounded concepts.

### Frontload

Allowed data shapes:

- structured preschool lessons
- structured K-8 lessons
- short readings with questions
- arithmetic and quantity drills
- time, space, nature, body, social, and cause/effect lessons

Forbidden data shapes:

- lessons whose prerequisite concept cards have not passed
- long source ingestion without reportable checks
- philosophical identity/reasoning material as a substitute for school foundations

### Evaluate

Probe families:

- grade-level factual probes
- arithmetic probes
- short explanation probes
- reading-comprehension probes
- prerequisite-retention probes
- protected-anchor probes

Metrics:

- grade-level answer correctness
- prerequisite retention after interference
- malformed/repetition rate
- protected-anchor status
- unknown-boundary status

Non-goals:

- adult-level expertise
- open-ended source learning

### Success Gates

Starting defaults:

- grade-band probe sets pass configured thresholds
- prerequisite concept reviews pass after school updates
- protected anchors pass
- malformed/repetition rates remain under threshold

Failure interpretation: missing prerequisite, lesson-order problem, or interference.

---

## Phase 5 - Reflective And Identity Training

**Goal:** identity stability, epistemic humility, and stepwise reasoning.

### Frontload

Allowed data shapes:

- identity anchors
- unknown-boundary anchors
- `I do not know` and `I need help` patterns
- short stepwise reasoning examples
- philosophy and reflection dialogues
- difficult-problem humility drills

Forbidden data shapes:

- unsupported claims of certainty
- identity-violating examples
- training from hallucinated answers

### Evaluate

Probe families:

- identity probes
- unknown-boundary probes
- uncertainty probes
- short reasoning probes
- contradiction probes
- source-learning readiness probes

Metrics:

- identity-anchor pass rate
- unknown-boundary pass rate
- appropriate-uncertainty rate
- reasoning-step coherence
- protected-anchor status

Non-goals:

- unrestricted web/source learning
- long autonomous research

### Success Gates

Starting defaults:

- identity and unknown-boundary protected anchors pass
- uncertainty probes pass
- short reasoning probes are coherent enough for supervised source learning
- no high-severity confabulation pattern persists

Failure interpretation: reflective-control weakness or protected-anchor regression.

---

## Phase 6 - Open Learning Readiness

**Goal:** prepare Ninereeds to learn from chats, texts, and summarized sources without
losing identity or epistemic boundaries.

This phase is intentionally last. Do not use open source learning to compensate for weak
form control, weak concept grounding, or weak school foundations.

### Frontload

Allowed data shapes:

- short source snippets with supervised summaries
- source-grounded Q&A
- correction-aware chat excerpts
- provenance and uncertainty drills

Forbidden data shapes:

- unsupervised bulk ingestion
- unverified raw web text
- source-free claims of knowledge

### Evaluate

Probe families:

- source-grounded answer probes
- summary fidelity probes
- refusal/uncertainty probes
- protected-anchor probes
- retention probes after new-source learning

Metrics:

- source fidelity
- summary accuracy
- uncertainty appropriateness
- protected-anchor status
- prior-concept retention

Non-goals:

- unrestricted autonomy
- ungated continuous learning

### Success Gates

Starting defaults:

- source-grounded probes pass
- summaries preserve key facts without invented claims
- uncertainty and identity anchors pass
- prior concepts survive source-learning updates

Failure interpretation: not ready for broad source learning.
