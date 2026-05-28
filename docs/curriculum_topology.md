# Curriculum Topology

A structured snapshot of the Ninereeds corpus and training history, designed to be
fed into deep research tools (GPT Deep Research, Gemini Deep Research) to generate
curriculum ordering proposals.

**Status: stub — to be completed after Phase G2 fix pass and wiki localization are done.**

---

## Purpose

The goal is to derive an optimal curriculum ordering for run_13 and beyond by combining:
- the full structure of what has been taught,
- vocabulary and concept dependencies,
- empirical evidence from runs 1–6 about what works and what breaks,
- known failure modes and their suspected causes,
- a clear definition of success.

Deep research will be asked to produce ordering proposals. These will be cross-referenced
against the grammar_plan.md ordering and our own intuitions before being adopted.

---

## Contents to include

### 1. Full file tree

Generated snapshot of `training_data/` — directory structure, file counts per corpus
layer, naming conventions. Enough for a research tool to understand what exists and
how it is organized.

```
training_data/
  phases/phase_1–6/        5,806 EN files + 3× localizations (DE/JP/ZH)
  grammar/00–10/            ~1,500 files, function-first case curriculum
  lang/lang_1–5/            ~12k files, multilingual vocabulary curriculum
  wiki/level_1–4/           2,111 EN files + 3× localizations (in progress)
  triplet_stories/tier_1–4/ 1,345 EN files × 4 languages
  reasoning/                27 EN files × 4 languages
  philosophy/               144 multilingual files
```

### 2. Allowlist and introduced vocabulary

`inventory/allowlist.txt` — the gated content word list. Every concept Ninereeds has
been explicitly taught. This is the vocabulary dependency map in raw form.

Relevant for ordering: a concept cannot be taught before its prerequisite vocabulary
exists. The allowlist reveals implicit dependencies.

### 3. Phase definitions and schemas

The `[user]/[Ninereeds]` corpus structure:
- 4 pairs per phase file
- Q1: appearance / what does X look like
- Q2: location / where is X found
- Q3: function / what does X do
- Q4: flexible — give, produce, cause, or natural English equivalent

Grammar corpus schema:
- 4–8 pairs per file
- EN + DE + JP + ZH parallel lines
- German case form must match cluster target

### 4. Existing cluster labels

From run reports and probe logs — what Ninereeds demonstrably learned:
- Spatial relations (static: auf/in/über + ある/いる)
- Dative transfer (partial — instability remains)
- Object accusative (partial)
- Arithmetic retrieval (brittle — framing-sensitive)
- Multilingual routing (present but degrades under loop pressure)

To be expanded with brain_map.md Phase 1 results once run_13 completes.

### 5. Run reports 1–6 (especially run_4)

Key empirical findings from `training/logs/`:

**run_1** — concatenated corpus, baseline. Established that format matters more than volume.

**run_4** — *(key reference)* best overall shaped score to date. Identified the epoch
sweet spot. First clear evidence of dative routing forming. Also first appearance of
book loop under sustained repetition pressure.

**run_5–7** — confirmed: small well-formed files outperform oversampling. Format match
to training schema is the strongest single predictor of retention.

**run_10–12** — scaling ablation. 25M → 151M → 604M. Depth fixed at 6. Per-layer weights
at 151M opened capability headroom. 512-dim at 604M showed capacity but needed more data.

Full reports: `training/logs/run_N_report.md`.

### 6. Known failure modes

**Book loop** — model enters a repetitive generation cycle under sustained output pressure.
Suspected cause: insufficient variation in training sequence + no diversity forcing in
inference. Minimized by loop count gate in shaped score.

**JP garbling** — Japanese output degrades to phonetic approximations or mixed-script
output after several turns. Suspected cause: JP localization calques in early corpus
(pre-2026-05-28 prompt fix) training incorrect token patterns.

**Dative/accusative instability** — model alternates between correct and incorrect case
forms within a single response. Suspected cause: insufficient contrast examples before
mixed use; grammar corpus is designed to address this directly.

**Arithmetic retrieval framing** — correct numerical relationships are present but only
surface under specific question framing. Rephrased questions get wrong or empty answers.
Suspected cause: math examples too homogeneous in surface form; model learned the form,
not the underlying operation.

### 7. Target objective

A curriculum ordering is successful if it produces a checkpoint with:

- **Stable shaped score** — promotion gate sustained across at least 3 probe rounds
- **Minimal loops** — loop count ≤ 3 in standard eval; ≤ 1 in grammar probes
- **No pronoun/negation bleed** — zero instances in any [Ninereeds] output block
- **Preserved multilingual structure** — DE/JP/ZH outputs maintain correct register,
  script, and grammar independently without cross-contamination
- **Dative/accusative stability** — correct case form on primary grammar probes with
  no alternation within a single response
- **Arithmetic retrieval robustness** — correct answer rate stable across ≥ 3 surface
  rephrasings of the same underlying problem

---

## How to use this document

1. Compile the full snapshot (file tree + allowlist + run reports) into a single brief.
2. Feed to GPT Deep Research and Gemini Deep Research separately, asking each to:
   - Identify implicit dependency orderings in the vocabulary and grammar layers
   - Flag any corpus ordering that violates a prerequisite relationship
   - Propose a curriculum sequence optimized for the target objective
   - Flag known failure modes and suggest structural mitigations
3. Cross-reference the two proposals against `docs/grammar_plan.md`.
4. Adopt points of agreement; debate divergences against empirical run data.
5. Update `training_data/grammar/manifest.md` and corpus builder ordering to reflect
   the final decision.

---

## Related docs

- `docs/grammar_plan.md` — existing function-first ordering rationale
- `docs/brain_map.md` — cluster labeling plan (feeds into section 4)
- `docs/training.md` — training procedure
- `training/logs/` — run reports
- `todo.md` Phase H — ordering manifests
