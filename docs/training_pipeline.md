# BDH Training Pipeline

Canonical description of every corpus layer, its purpose, and the intended training sequence.

Last updated: 2026-05-15

---

## Corpus layers

### Lang curriculum — `training_data/lang/`

**Status:** Complete (all five sublevels, all four languages)

The most granular layer. Teaches vocabulary and grammatical structure explicitly and
multilingually before any of that vocabulary appears in contextual use.

| Sublevel | Dir | Files | Content |
|---|---|---|---|
| lang_1 | `lang_1/` | ~5 k | One file per allowlist word; four-language vocabulary pairs |
| lang_2 | `lang_2/` | ~6 k | Semantic frames: verbs, adjectives, nouns, pronouns, combinations |
| lang_3 | `lang_3/` | 615 | Dative constructions (3a/3b), reflexive + benefactive (3c), parallel stories (3d) |
| lang_4 | `lang_4/` | 316 | Static location (4a), movement (4b), instrument (4c), parallel stories (4d) |
| lang_5 | `lang_5/` | 192 | Question answering: wer/wen/wem/wessen (5a), spatial (5b), temporal (5c), causal (5d + stories), modal (5e), yes/no + doch (5f) |

All lang files are four-language parallel: EN, DE, JP (plain form), ZH (Traditional).
German uses V2 word order and correct Perfekt auxiliary selection.
Japanese uses plain form throughout (no romaji).
Chinese uses Traditional characters and Standard Written register.

Allowlist at `inventory/allowlist.txt` gates which content words are permitted in lang files
and downstream story layers. Any new word that appears in corpus generation must be added
to the allowlist after review.

---

### Phase curriculum — `training_data/phases/`

**Status:** Complete (phases 1–6)

English-only structured dialogue files. The authoritative concept definition layer.

Each file follows the strict `[user]`/`[Ninereeds]` format:
exactly four block pairs, five body lines per Ninereeds response, no pronouns,
no negation, one sentence per line. Malformed files have outsized training impact
at this model size.

| Phase | Content |
|---|---|
| Phase 1–2 | Core concrete vocabulary and basic properties |
| Phase 3–5 | Expanded concept coverage, relational and social knowledge |
| Phase 6 | Bridge curriculum: scaffold words (word, sentence, thought, idea, true, real, question, answer, plan, goal) and connective tissue concepts |

Training uses `training_data/phases/training_sequence.txt` as the authoritative ordering,
not raw filename order.

Key references:
- `training_data/phases/concept_index.md`
- `training_data/phases/training_sequence.txt`
- `inventory/dependency_graph.json`

---

### Reasoning — `training_data/reasoning/`

**Status:** Complete (27 EN source files × 4 languages = 108 files)

Math and logic training. Two structural types:

- **Math fact files:** symbolic notation (`1 + 1 = 2`), verbal mode, grounded story mode,
  reasoning chain. The symbolic notation is language-universal; verbal and story modes
  are fully localized.
- **Logic and reasoning files:** conditional (if/then), contradiction checks, epistemic
  uncertainty, symbolic substitution, ordinal sequencing, conservation of quantity, etc.

Language registers:
- DE: German textbook style (Schulbuch) — precise, not academic
- JP: plain form (常体), light and natural — not stiff or academic
- ZH: Standard Written Chinese, no spoken particles

Semantic preservation is critical in math story modes: if the English has
"a bird finds one worm," every language version must have a bird finding a worm,
not a bird finding another bird.

File naming: `filename.md` (EN), `filename_DE.md`, `filename_JP.md`, `filename_ZH.md`.

---

### Triplet stories — `training_data/triplet_stories/`

**Status:** Complete (1 345 EN files × 4 languages = 5 380 files)

Narrative contextualization of vocabulary. Four tiers of increasing complexity.
13 categories: abstract concepts, animals and nature, body and health, food and meals,
home and daily life, language and grammar, math and science, people and relationships,
play and games, school and learning, tools and making, vehicles and travel,
weather and seasons.

Each file is one story: a `[user]` prompt and a `[Ninereeds]` narrative response.
Language registers:
- DE: natural narrative German (Lesebuch style), Präteritum or Perfekt
- JP: plain past tense (〜た), short sentences, タメ口 narrative
- ZH: natural narrative Traditional Chinese, no spoken particles

File naming: `category_NN_EN.md`, `category_NN_DE.md`, `category_NN_JP.md`, `category_NN_ZH.md`
within `tier_1/` through `tier_4/`.

---

### Wiki — `training_data/wiki/`

**Status:** Levels 1 and 2 complete; Level 3+ deferred

Broader concept knowledge beyond the phase curriculum. Child-facing explanatory language,
category ownership, relational knowledge.

Expansion follows a strict alternating cadence with story layers — see Stage 7.

---

### Philosophy — `training_data/philosophy/`

**Status:** Complete (144 multilingual files)

Abstract philosophical dialogues. Socratic structure: a statement, a challenge,
a response, and a final open reflection from the user that receives no answer.
That final unanswered turn is intentional — it models that not every thought
requires a resolution.

Each file uses language-tagged blocks:
`[STATEMENT_EN/DE/JA/ZH]`, `[USER_EN/DE/JA/ZH]`, `[NINEREEDS_EN/DE/JA/ZH]`.

Language registers:
- DE: serious philosophical prose (German essay or school text level)
- JA: である体 for STATEMENT and NINEREEDS; natural conversational for USER
- ZH: Standard Written Chinese, no spoken particles

File naming: `dialogues_catN_NN.md` (12 categories × 12 entries = 144 files).

---

## Training sequence

The corpus has two parallel foundations — lang and phases — that are complementary:
phases teach *what things are*, lang teaches *how to talk about them in four languages*.
Neither is strictly prerequisite to the other; they interleave naturally.

### Stage 1 — Lang 1–2 + Phases 1–3

Run together. Lang 1–2 establishes the multilingual vocabulary base;
phases 1–3 establish core concept definitions and strict formatting.
These reinforce each other: the model learns a word in four languages (lang_1)
and separately learns what that concept is (phase).

Exit condition:
- Model handles basic vocabulary and concept definitions stably.
- Phase formatting is respected.

---

### Stage 2 — Lang 3–4 + Phases 4–6

Lang 3–4 introduces grammatical constructions (dative, reflexive, spatial, movement,
instrument). Phases 4–6 extend concept coverage and introduce bridge vocabulary.

Exit condition:
- Model handles dative and spatial constructions correctly in all four languages.
- Phase 6 bridge words (word, sentence, plan, goal, etc.) are stable.

---

### Stage 3 — Lang 5 + Reasoning

Lang 5 introduces question answering (who, what, where, when, why, how, yes/no + doch).
Reasoning files introduce math and logic patterns in all four languages.

These belong together: both are interrogative and deductive, and running them together
lets the model encounter "how do you answer a question" and "how do you reason to an
answer" as a coherent block.

Exit condition:
- Model answers wer/wen/wem/wessen, wo/wohin/woher, wann/warum/wie correctly.
- Model handles simple addition, subtraction, conditionals, contradiction checks.
- Semantic preservation holds across languages (objects, actors, counts are stable).

---

### Stage 4 — Triplet stories (tiers 1–2)

First narrative layer. Concrete, daily-life stories using grounded vocabulary.
Only allowlisted vocabulary should appear; the allowlist was built with these
stories in mind.

Run tiers 1–2 before tiers 3–4 to establish the narrative voice before
increasing complexity.

Exit condition:
- Model produces coherent narrative responses across all four languages.
- No vocabulary bleed from ungrounded sources.

---

### Stage 5 — Wiki Level 1 audit

Before proceeding to richer content, audit the wiki Level 1 corpus:
- category ownership
- overlap control
- contrast cleanliness
- dependency coverage
- voice consistency

This audit is not just a completeness check — it asks whether Level 1 is
teachable as a coherent whole.

Exit condition:
- Level 1 is stable enough to compare against the phase foundation.

---

### Stage 6 — Level 1 vs phases grounding audit

Does the model have enough phase support to absorb Level 1 wiki cleanly?
Classify important wiki concepts as:
- grounded in phases
- weakly grounded
- missing curriculum anchor
- better left wiki-only

If grounding is weak, fix or log the gaps before continuing.

Exit condition:
- Major wiki concepts are either grounded, explicitly deferred, or logged as gaps.

---

### Stage 7 — Triplet stories (tiers 3–4) + Wiki Level 2

Alternating cadence. Do not front-load stories with vocabulary from a wiki level
that does not yet exist.

```
Wiki L1 → Triplet 1–2 → Wiki L2 → Triplet 3–4 → Wiki L3 → Triplet + philosophy → …
```

Level 2 should not begin automatically because Level 1 is "done."
Begin only after the Level 1 and grounding audits pass.

When opening Level 2:
- review sample outputs
- confirm style and abstraction level match the target
- refine category plans before large-scale expansion

Exit condition:
- Triplet tiers 3–4 stable in all four languages.
- Wiki Level 2 articles quality-passed.

---

### Stage 8 — Philosophy

Run after the model has a stable narrative and conceptual base.
Philosophy dialogues are abstract and dialectical; they require the model
to already handle nuanced multi-turn reasoning before they are productive.

The multilingual tag format (`[STATEMENT_EN]` / `[STATEMENT_DE]` etc.)
means the model sees the same philosophical idea expressed in four registers
simultaneously, which reinforces the idea that the logical content is
language-independent.

Philosophy may be delayed or introduced gradually if abstraction causes instability.

Exit condition:
- Model engages coherently with the Socratic structure across all four languages.
- The unanswered final USER turn does not trigger a spurious response.

---

### Stage 9 — Mommy Says Machine evaluation

Mommy Says Machine is primarily an evaluation and diagnostic system,
not a training component.

Use after a full training pass when the model is expected to be near
target competence. Best use cases:
- concepts clearly defined but failing in practice
- false belief and hidden-state failures
- correction response quality
- within-session retention

Stable failure patterns can feed a targeted correction-pair batch
for a subsequent offline training run.

See `docs/mommy_says_machine.md` for full protocol.

---

## Human review checkpoints

1. **Before Stage 5 (wiki audit):** review stage 1–4 output quality; confirm
   multilingual registers are stable; confirm allowlist is up to date.

2. **Before Stage 7 (Level 2):** review Level 1 quality; review grounding audit;
   confirm story narrative voice matches target.

3. **Before Stage 8 (philosophy):** confirm the model handles multi-turn abstract
   dialogue without collapsing into single-sentence answers.

4. **Before using Mommy Says Machine correction data for training:** inspect whether
   failures are real concept failures or prompt-format artifacts; inspect whether
   teacher corrections are actually the kind of signal worth training on.

---

## Related files

- `inventory/allowlist.txt` — content word gate for lang and story layers
- `inventory/dependency_graph.json` — phase dependency graph
- `training_data/phases/training_sequence.txt` — authoritative phase order
- `training_data/phases/concept_index.md`
- `docs/mommy_says_machine.md`
- `docs/training_harness_design.md`
