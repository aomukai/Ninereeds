# Ninereeds Training Reference

Combines the training harness design and the step-by-step training manual.
Single source of truth for how to run, evaluate, and improve the model.

Last updated: 2026-05-23

---

## What Ninereeds is

Ninereeds is a small (~25M parameter) Hebbian-trained **Developmental Learner Model (DLM)**.
It is not a scaled language model — there is no error averaging from scale, so every malformed
training file has outsized impact. The goal is not broad factual coverage but a coherent,
well-grounded knowledge structure built from a hand-crafted curriculum.

Key properties of the architecture and training approach:
- **Semantic clustering matters.** Grouping related concepts (animals → body → food) lets the
  model build category-level associations. Alphabetical ordering gives zero semantic co-occurrence
  between adjacent concepts. This was confirmed empirically in run_4 (+0.018 shaped over run_3).
- **Stories are the grounding substrate.** Phase files teach *what things are* in isolation.
  Grounded stories teach *how things act and relate* — causal verbs, spatial relations,
  character continuity. Story grounding transfers into phase-format responses as the
  "Battling is to [verb]" pattern.
- **Interleaving preferred over isolated fine-tuning.** Running any corpus layer as 100%
  saturation (run_2) causes catastrophic forgetting at E1 and format collapse. Interleaved
  at ≤ 5% of corpus, the same signal transfers without disruption.
- **Shaped score is the primary metric.** The prompt shaper is part of the live inference
  pipeline. A checkpoint that scores well raw but poorly shaped is not useful.
- **E2–E4 sweet spots are likely an architecture property.** E1 is always Adam warmup noise.
  E5+ is always memorisation overfit. The exact sweet spot shifts with intervention intensity:
  milder changes peak earlier (E2), more disruptive changes peak later (E4).

---

## Part 1 — Harness

### Doctrine

The harness exists to improve the model through explicit, auditable interventions
rather than opaque self-modification.

Core rules:
- One major intervention per run. Never combine two changes.
- Transparency over opacity. Every decision is justified by evidence from the previous report.
- Human oversight at the strategic level. Co-Researcher (Claude/Codex) plans and executes; the user sets direction.
- Bias toward reversibility. Relevant checkpoints are kept; nothing is silently overwritten.

BDH architecture note: the BDH paper demonstrates a direct merge (concatenate neuron-dimension
tensors, average shared tensors) where the merged model retained meaningful capabilities and
improved quickly with a small post-merge training pass. Branch–specialise–integrate is a
valid future design pattern. Raw merges require a repair phase before mainline promotion.

---

### Evaluation

#### Tools

```bash
# Probes — qualitative output quality across 12 prompt categories
python meta/scripts/probe.py --checkpoint $CKPT --temperature 0.7 --tokens 120

# Eval — quantitative shaped and raw scores across 18 prompts
python eval.py --checkpoint $CKPT
```

Run both after every epoch checkpoint, immediately when the checkpoint file appears.
Do not skip either tool. Do not defer eval to after the run completes.

#### Primary metric: shaped score

The eval produces two scores: **raw** and **shaped**.

- **Raw**: average score of direct model completions.
- **Shaped**: average score after the prompt shaper routes each prompt to the appropriate
  format before inference. The shaper is part of the live inference pipeline.

**Shaped is the primary metric.** A checkpoint with raw 0.921 / shaped 0.892 (run_3 E3)
is worse than one with raw 0.898 / shaped 0.925 (run_3 E2), despite better raw.

A strongly negative shaped delta (shaped << raw) means the model has learned content
patterns the shaper penalises — typically language-register bleed or format mismatch.

#### Probe categories

Twelve probes in three groups:

| Group | Probes | What they test |
|---|---|---|
| Phase format | concrete noun, abstract adj, gerund, bridge word | `[user]/[Ninereeds]` format; no pronouns; no negation; 5-line structure |
| Lang curriculum | lang_1 vocab, lang_2 semantic, lang_4 spatial, lang_5 Q&A | 4-stanza EN/DE/JP/ZH structure |
| Narrative + reasoning | triplet DE, triplet JP, reasoning number, reasoning arithmetic | Story continuation and math output |

Probe summary flags: garbled/12, sentences/12, pronouns/12, negation/12.
Zero pronouns and zero negation in phase probes is the target state.

#### Failure modes

| Mode | Description | Severity |
|---|---|---|
| Loop | Model repeats a phrase or sentence until token limit | High — degrades shaped score; promotes to eval failure |
| Abrupt stop | Response ends mid-sentence | Medium — eval penalty; watch for trend across epochs |
| Garbled output | UTF-8 replacement chars or incoherent character sequences | Medium — persistent in JP triplets across all runs |
| Philosophy tag bleed | `[STATEMENT_DE]` or `[USER_DE]` appearing in open-ended completions | Medium — first seen at run_3 E3, worsens with more epochs |
| Reasoning vocab bleed | "number", "equals", "count" appearing in abstract adj or bridge word probes | Medium — caused by `oversample_cluster` at high dose |
| "A book is" loop | Specific prompt reliably triggers a loop from run_4 E4 onward | Low-medium — single-prompt issue, persistent |

---

### Intervention registry

#### Layer 1 — base interventions (currently active)

| ID | Intervention | When to use | Known constraints |
|---|---|---|---|
| L1-A | `train_longer` | Shaped score still rising at final epoch | Sweet spot is typically E2–E4; past E5 all runs have memorised |
| L1-B | `teacher_student_drill` | One concept cluster persistently wrong; existing files aren't fixing it | Requires new file generation via DeepSeek; needs API key |
| L1-C | `oversample_cluster` | One section under-weighted; known-good signal drowned out | ×4 causes cross-domain bleed (run_5); ×2 is the calibrated starting point |
| L1-D | `reorder_curriculum` | Alphabetical or current ordering places unrelated concepts adjacent | Used in run_3 (stories interleaved) and run_4 (phase semantic cluster) |
| L1-E | `add_contrastive_pairs` | Model confuses two concepts that are close but distinct | Requires new data generation; high effort |
| L1-F | `simplify_wording` | Structurally correct but semantically confused output on a specific concept | Requires corpus rewriting; medium effort |
| L1-G | `verify_teacher_output` | New corpus section added whose quality is unverified | Gate, not a training intervention |
| L1-H | `request_more_data` | All Layer 1 options tried with no sustained improvement | Human escalation |
| L1-I | `msm_correction` | Specific, repeating, identifiable output error (wrong case, wrong answer, persistent garble) that probe shows clearly | Minimally invasive — targets a narrow failure; `machine.py` not yet implemented but workflow is executable manually; see protocol below |

##### L1-I protocol — `msm_correction`

The Mommy Says Machine generates small, vocab-guarded correction pairs for a specific
failing pattern, applies them in a short training pass, and immediately probes retention.
This is the lightest available intervention — use it when you can name the exact error.

```
1. Identify the failure from probe output.
   Example: probe shows "über den Berg" but training data has "über dem Berg" (dative).

2. Generate correction pairs in standard [user]/[Ninereeds] format.
   - Teacher restates the correct form: no explanation, no praise, ≤2 sentences.
   - All words must be in inventory/allowlist.txt (vocab guard).
   - 10–30 pairs is enough; more risks overfit on the correction itself.
   - Use DeepSeek (mommy-says schema from docs/mommy_says_machine.md Section 6) or write manually.

3. Run a short training pass on the correction pairs only:
     python train.py --phase 0 --corpus-file tmp/msm_correction.txt \
       --output core/run_N_eK_msm_patch.pt \
       --resume checkpoints/run_N_eK.pt \
       --epochs 1 --amp-bf16

4. Run probe.py on the patched checkpoint.
   Does the target probe now produce the correct output?

5. Conditional promote:
   - Retained (probe correct):  cp core/run_N_eK_msm_patch.pt checkpoints/run_N_eK_msm.pt
   - Not retained (probe wrong): discard — do not promote; consider L1-E (contrastive pairs) instead.

6. Document in the run report: what was corrected, how many pairs, retention result,
   shaped score before/after (run eval.py on both checkpoints).
```

Checkpoint naming for MSM patches: `checkpoints/runN_eK_msm.pt` — suffix `_msm` marks it
as a patch on top of a promoted checkpoint, not a full corpus run.

Full MSM design (multi-pass baseline → correction → retention loop): `docs/mommy_says_machine.md`.

---

#### Layer 2 — branching and retention (Phase 2 — not yet active)

| Intervention | Description |
|---|---|
| `compare_branch` | Compare two branches on the campaign objective |
| `merge_candidate` | Propose and evaluate a merge of two branches |
| `retention_probe` | Test whether knowledge survives a distractor sequence |

#### Layer 3 — merge lifecycle (Phase 2 — not yet active)

| Intervention | Description |
|---|---|
| `premerge_align` | Weight alignment before merging when geometric misalignment is the issue |
| `postmerge_repair` | Brief joint rehearsal or corrective LoRA after a merge that passes most evaluations |

Merge recipe escalation: task arithmetic → TIES/DARE (if interference) → Git Re-Basin
(if geometric misalignment) → postmerge_repair (if calibration drift after otherwise passing merge).

#### Layer 4 — corpus and language layer interventions

| Intervention | Description |
|---|---|
| `language_isolate` | Evaluate a single language layer to isolate cross-language interference |
| `layer_gate_probe` | Test whether a new corpus layer degrades an earlier layer |
| `register_correction` | Targeted retraining on a specific language register that has drifted |
| `localization_audit` | Verify semantic fidelity across EN/DE/JP/ZH |
| `allowlist_gate` | Halt expansion if new story or lang file introduces out-of-allowlist vocabulary |
| `cross_layer_probe` | Test whether the model applies knowledge across corpus layers |
| `philosophy_register_probe` | Verify である体 / Schulbuch / written Chinese register stability |

---

### Conventions

#### Run naming

| Artefact | Pattern | Example |
|---|---|---|
| Corpus | `training/corpus/run_N_[name].txt` | `run6_corpus.txt` |
| Training output | `core/run_N_[name].pt` | `core/run_6_oversample_reasoning_x2.pt` |
| Epoch checkpoint | `core/run_N_[name]_eK.pt` | `core/run_6_oversample_reasoning_x2_e2.pt` |
| Best checkpoint | `checkpoints/run_N_eK.pt` | `checkpoints/run6_e2.pt` |
| Training log | `training/logs/run_N_train.log` | `training/logs/run_6_train.log` |
| Report | `training/logs/run_N_report.md` | `training/logs/run_6_report.md` |

Intervention name in filename: short, lowercase, underscored.

#### Checkpoint retention

- Keep all per-epoch `core/` checkpoints until the run is fully evaluated.
- Step 8 handles promotion and cleanup automatically: copy best to `checkpoints/`, confirm,
  then `find`-delete the other epoch files for that run. Never delete checkpoints by hand.
- Never delete a `checkpoints/` entry that is the base for a subsequent run.
- The all-time best checkpoint is never deleted. Currently: `checkpoints/run4_e4.pt`.
- `core/*.pt` and `checkpoints/` are both gitignored — all weights are local-only.

#### Report format

One file per run: `training/logs/run_N_report.md`.

Required sections:
1. **Setup table** — run name, base checkpoint, corpus, change description, epochs, LR, AMP
2. **Motivation** — hypothesis and why this intervention was chosen
3. **Epoch sections** (one per epoch) — loss, probe results, eval results, notes
4. **Summary table** — all epochs: loss / raw / shaped / loops / abrupt / best candidate?
5. **Selected checkpoint** — path and justification
6. **Key observations** — what worked, what didn't, what to try next
7. **Comparison table** — this run vs the previous run (same epoch slots)

#### Epoch count

- **3 epochs** when base checkpoint is strong (shaped ≥ 0.925) and intervention is targeted.
- **5 epochs** when testing a new curriculum ordering or structural corpus change.
- Never train past the memorisation cliff: E5+ has regressed in every observed run.

#### Platform notes

- Python: `/home/aomukai/.unsloth/studio/unsloth_studio/bin/python`
- Always pass `--amp-bf16`. Without it, OOM on RTX 3060 (10.4 GB allocated vs 11.6 GB available).
- Ordered-curriculum runs must pass `--no-shuffle`. Seeded shuffling is reproducible,
  but it still destroys intended file order.
- Log output is stdout-buffered when redirected. Epoch summary lines appear ~5–10 min late.
  Use checkpoint file existence as the reliable epoch-complete signal, not the log tail.
- Optimizer state is always reset on resume (`weights_only=True` in `load_checkpoint`).
  E1 Adam warmup noise is expected even from a strong base checkpoint.

---

### Stop conditions

Pause and review with the user when any of the following is true:

| Condition | Action |
|---|---|
| Shaped ≥ 0.970 for 2 consecutive epochs | Convergence — run full MSM baseline evaluation (all concepts); shift focus to targeted MSM corrections |
| Shaped has not improved over 3 consecutive runs | Escalate: `request_more_data` or human review |
| Loops ≥ 4 on any checkpoint | Do not promote; investigate before next run |
| Abrupt stops ≥ 2 on any checkpoint | Do not promote; investigate |
| All Layer 1 interventions tried without sustained improvement | Escalate to Layer 2 or human review |

---

### Empirical findings

Findings from runs 1–6 that inform future intervention choices.

#### Epoch sweet spots

| Run | Intervention | Sweet spot | Shaped peak | Why |
|---|---|---|---|---|
| run_1 | baseline | E3 of 5 | — | Standard pattern |
| run_2 | story fine-tune (separate) | E3 | 0.922 | E1 catastrophic forgetting; E3 recovery |
| run_3 | stories interleaved | E2 of 3 | 0.925 | No forgetting; richer content causes E3 shaper conflict |
| run_4 | phase semantic cluster | E4 of 5 | 0.943 | Cluster ordering delays sweet spot 2 epochs; higher ceiling |
| run_5 | reasoning ×4 | E1 of 3 | 0.923 (shaped) / E2 for reasoning probes | ×4 causes bleed; shaped oscillates |

Pattern: the sweet spot shifts later when the intervention is more disruptive to existing routing.
Alphabetical → semantic cluster moved it from E3 to E4. Over-aggressive oversampling makes it unstable.

#### Oversample dosing

- ×4 (run_5): reasoning vocabulary bleeds into abstract adj and bridge word probes.
  Loop count rose from 1 (run_4 E4 baseline) to 3. Shaped peaked at 0.924 — below baseline.
  Correct arithmetic ("two plus two is four") did appear at E2, confirming the mechanism.
- ×2 (run_6): no arithmetic breakthrough at any epoch. Shaped peaked 0.916 — below 0.943 baseline.
  Root cause: format mismatch, not dose. `oversample_cluster` is exhausted for arithmetic.
- Rule of thumb: start at ×2 for any new oversample target. Only increase if no transfer is observed.
  If ×2 also fails, the problem is likely retrieval framing rather than corpus weight — use `teacher_student_drill` instead.

#### Story grounding transfer

"Battling is to [verb]" pattern (story grounding transfer signal) survived all 5 run_4 epochs
and all 3 run_5 epochs. Robust to curriculum reordering and oversampling at ×2–×4.
It weakened slightly at run_5 E3 (reverted to "Battling is a [noun]" under heavy oversampling).

#### Catastrophic forgetting

Running stories as a **separate** fine-tune on 100% story data (run_2) caused E1 catastrophic
forgetting — format-domain collapse, shaped 0.943 at E1 was misleadingly high because story
format dominated inference, not because the model was broadly capable.
**Do not run any corpus layer as a 100% saturation fine-tune.** Interleave at ≤ 5% of corpus.

#### German and Japanese spatial

- German spatial structure first appeared at run_3 E3 and has been stable since.
  However, the model consistently produces the **accusative** "über den Berg" rather than the
  correct **dative** "über dem Berg" for static location. The training data (`4a_above_be.md`)
  has the correct dative form, but "über den" appears 42× vs "über dem" 12× in lang_4 overall
  (mostly movement-context stories), and the model has over-learned the accusative.
  The structural pattern is there; the case distinction is not reliably learned.
  Note: "über dem Berg" appeared spontaneously at run_6 E3 — the knowledge is latent and
  retrievable under sufficient training pressure, but not yet the stable default.
- Japanese spatial ("雲が山の上にある") first appeared correctly at run_4 E4.
- Spatial prepositions are a reliable late-epoch signal for structural learning, but
  German dative/accusative distinction under two-way prepositions remains an open problem.

**Dative drill sequencing:** the two-way prepositions (über, an, auf, in) require a
static/movement judgement under production pressure — the hardest case. The right Phase A
entry point for dative is the **always-dative prepositions** (mit, bei, von, aus, nach, zu,
seit, gegenüber) which are unconditional: no semantic reasoning required, just cue-to-case
mapping. Drilling these first builds the dative retrieval pathway. Once "mit dem Mann" is
stable, "über dem Berg" becomes reachable because the pathway is already warm.

This mirrors the human SLA pattern: students who know the dative rule can still fail to
produce it reliably under pressure, because understanding ≠ retrieval under load. The
always-dative prepositions are the anchor set — high frequency, zero ambiguity, same
mechanism as Phase A arithmetic drills. Two-way prepositions come after the anchor is built.

Current lang_4 starts directly with two-way prepositions without establishing the unconditional
dative reflex first. That is the structural gap to address — not a corpus rebalance, but
a sequencing problem.

#### Reasoning

Arithmetic and number understanding had zero correct outputs through run_1–run_4.
run_5 ×4 oversampling first produced "Two plus two is four" at E2 — confirming the mechanism
exists — but gains regressed at E3 and caused cross-domain bleed.
run_6 ×2 produced no arithmetic breakthrough at any epoch (shaped peaked 0.916 < 0.943 baseline).

**Root cause identified (run_6 analysis):** the existing reasoning files all use a "Teach me
about..." / multi-modal format (Symbolic Mode / Verbal Mode / Grounded Story Mode / Reasoning
Chain). The probe asks "what is two plus two?" in direct Q&A style. This surface-form mismatch
means the training signal and retrieval cue are not aligned — the model has been trained on
one question frame and probed on another.

run_7 intervention: 12 drill files generated in exact probe format (what is X plus X? →
X plus X is Y.) to close the format gap. No oversampling — quality of signal over quantity.

#### Retrieval framing sensitivity

BDH appears unusually sensitive to the match between training question surface form and
inference question surface form. Evidence:

- Arithmetic facts in multi-modal "Teach me about" format did not transfer to "what is?" probes
  across 4 runs, despite the model eventually producing correct output under extreme oversampling
  pressure (×4). The signal was there; the retrieval frame was wrong.
- The "A book is" loop is stable from run_4 E4 onward — a specific retrieval frame locks the
  model into an attractor. Changing the question slightly ("What is a book?") may produce
  different routing than an open "A book is" prompt.
- German dative/accusative: the correct "über dem Berg" form appeared spontaneously at run_6 E3,
  after 3+ runs of producing the accusative. One extra epoch of the same training data pulled
  the latent correct form through — consistent with a retrieval threshold, not absent knowledge.

**Implication for curriculum design:** the model first needs an exact format match before
gradual paraphrase loosening can work. Do not assume semantic abstraction transfers from
one surface form to another. Use the 4-phase paraphrase curriculum below for any new
structured knowledge that needs to be reliably retrievable.

#### 4-phase paraphrase curriculum

For any structured fact that needs stable, broadly retrievable output (arithmetic, case
grammar, spatial prepositions, etc.), the training arc should be:

| Phase | Form | Example | Status for arithmetic |
|---|---|---|---|
| A | Exact mapping — training Q matches probe Q exactly | "What is two plus two?" → "Two plus two is four." | run_7 (in progress) |
| B | Paraphrase equivalence — multiple question framings, same fact | "What does two plus two equal?" / "How much is two plus two?" / "What is 2+2?" | Not yet generated |
| C | Multilingual equivalence — DE/JP/ZH variants of the same question | "Was ist zwei plus zwei?" | Partial (reasoning has DE/JP/ZH localizations of multi-modal files, not drill format) |
| D | Semantic abstraction — fact embedded in narrative/dialogue | "Biscuit gets four treats because Emma gave two and Taro gave two." | Partially done (triplet stories count quantities; no explicit arithmetic narrative) |

Phase D is largely already present in the corpus (grounded stories teach quantity and
causality). Phase C is partially present. The gap is Phase A (just filled by run_7 drill
files) and Phase B (not yet generated).

The right sequence: **do not advance to Phase B until Phase A produces stable exact retrieval.**
If run_7 E2 shows "Two plus two is four" consistently, generate Phase B files for run_8.
If run_7 fails, diagnose before adding paraphrase pressure — paraphrase on an unstable base
makes the problem harder, not easier.

This same 4-phase pattern likely applies to:
- German dative/accusative distinction (Phase A: rebalance lang_4; Phase B: paraphrase variations)
- Any new structured knowledge where the probe format differs from existing training format

---

### Open questions

Research questions that should guide future intervention choices. Update as evidence accumulates.

| Question | Status | Evidence so far |
|---|---|---|
| Can reasoning improve without bleed? | Partially answered | ×2 avoided bleed but produced no arithmetic transfer; root cause was retrieval framing, not dose |
| Does semantic clustering shift sweet spot earlier or later? | Answered (later) | run_4 sweet spot E4 vs run_3 E2 |
| Does story grounding persist under heavy oversampling? | Partially answered | "Battling is to [verb]" survived ×4, weakened at E3 |
| Can philosophy coexist without tag bleed? | Unanswered | [STATEMENT_DE] appeared in run_3 E3 open-ended prompts; not yet isolated |
| Are loops tied to over-specialised attractors? | Hypothesis | "A book is" loop stable from run_4 E4 onward; could be phase-format routing lock |
| Does Mommy Says Machine correction persist? | Active — available as L1-I at any time | Protocol added to registry; first candidate: German dative/accusative (über dem Berg) |
| Can JP garbling be eliminated without isolating JP training? | Unanswered | Persistent across all runs; may need `language_isolate` intervention |
| Can German dative/accusative distinction under two-way prepositions be taught? | Planned — after arithmetic stabilises | Root cause is sequencing, not imbalance: lang_4 starts with two-way prepositions without first anchoring always-dative prepositions (mit, bei, von, aus, nach, zu). Phase A drill: always-dative anchors first; two-way prepositions after the dative pathway is warm |
| Does `teacher_student_drill` outperform `oversample_cluster` for reasoning? | Active — run_7 | 12 drill files in exact probe format; hypothesis: format match produces stable arithmetic retrieval |
| Does paraphrase pressure produce stable, broadly retrievable arithmetic? | Planned — pending run_7 | Phase A (exact mapping) in run_7; Phase B (paraphrase variants) contingent on Phase A success |
| Is there a corpus weight threshold below which a section never transfers? | Partially answered | Retrieval framing may matter more than weight; reframing as Phase A drill fixed the approach |

---

### Branching and merge (Phase 2)

The following is designed for when mainline training plateaus and capability development
moves to specialist branches. Not currently active.

#### State model

**Round** — atomic unit. One major change only.

**Campaign** — persistent local-search unit. Cluster- or hypothesis-centred container
with a parent checkpoint, allowed interventions, stop conditions, and outcome classification.

**Frontier** — at most three live candidates per campaign:
- **Champion:** best current branch or merge path on the campaign objective.
- **Challenger:** most plausible alternative.
- **Explorer:** reserved for deliberate diversity when progress plateaus.

Branch state classes: `mainline`, `campaign_branch`, `merge_candidate`,
`archive_promising`, `archive_failed_but_informative`, `reverted_snapshot`.

#### Merge policy

Parent selection: homologous merging only — same BDH family, same tokenizer,
compatible tensor topology, preferably a shared checkpoint ancestor.

Recipe escalation:
1. Soup-style averaging / task arithmetic — close siblings, light specialisation
2. TIES or DARE — interference likely (sign conflict, redundant low-magnitude changes)
3. `premerge_align` + Git Re-Basin — geometric misalignment
4. `postmerge_repair` — calibration drift after an otherwise passing merge

BDH-native structural merge: concatenate along neuron dimension, average shared tensors.
Always run a repair phase before mainline promotion.

#### Promotion sequence

A branch moves to mainline only after clearing four comparisons:
1. Target improvement: branch vs. parent on the specific campaign goal.
2. Merge integrity: sandbox merge vs. winning branch.
3. Global safety: sandbox merge vs. mainline on the global regression suite.
4. Retention probe: merged model holds knowledge across a distractor sequence.

---

## Part 2 — Training manual

Step-by-step procedure for every run. Follow in order. Do not skip steps.

---

### Step 0 — Orient (run this first in every session)

Before doing anything else, establish the current state:

```bash
# Is training already running?
ps aux | grep train.py | grep -v grep

# What checkpoints exist for the current run?
ls -lh core/run_*_e*.pt 2>/dev/null | tail -10

# What does the current report say?
# Open training/logs/run_N_report.md and find the first (fill) line
```

Three possible states:

**A — Training is running.**
Do not launch a new run. Find the current epoch checkpoint file name from the training command
(`ps aux` output shows `--output core/run_N_[name].pt`; epoch files are `_eK.pt`).
Set up a background monitor for the next epoch:
```bash
until [ -f core/run_N_[name]_eK.pt ]; do sleep 60; done && echo "ready"
```
Then proceed to Step 7 (eval) for that epoch when it fires.

**B — Training has finished but the report has unfilled epochs.**
Identify which epoch checkpoints exist (`ls core/run_N_*_e*.pt`) and which are missing
from the report. Run probe + eval for each unfilled epoch in order, then complete the report.
Then proceed to Step 8 (select best checkpoint).

**C — The current run is complete and documented.**
Proceed to Step 1 (read the report) and choose the next intervention.

---

### Step 1 — Read the previous report

Open `training/logs/run_N-1_report.md`.
Read: summary table, selected checkpoint, key observations.
Identify the weakest area from probe results and the lowest shaped score.

**Do not proceed without reading the last report.**
Never make intervention decisions from memory or context alone — reports are the source of truth.

---

### Step 2 — State the current baseline

Write down before choosing anything:

| Field | Value |
|---|---|
| Best checkpoint | (path + shaped score + loop count) |
| Worst probe category | (e.g., "reasoning arithmetic — no equals structure") |
| Worst eval prompt | (prompt + shaped score) |
| Last intervention | (e.g., `oversample_cluster` ×4) |

---

### Step 3 — Choose exactly one intervention

Pick one entry from the Layer 1 intervention registry.

Rules:
- One and only one. Do not combine.
- Do not repeat the immediately preceding intervention unless the hypothesis was only partially tested (e.g., ×4 → ×2 is valid because the dose was wrong, not the intervention).
- Justify the choice in one sentence against evidence from the previous report.
- If you cannot justify from evidence, write `request_more_data`.

**Intervention history (update each run):**

| Run | Intervention | Peak shaped | Loops | Notes |
|---|---|---|---|---|
| run_1 | baseline | — | — | |
| run_2 | story fine-tune (separate) | 0.922 | — | E1 catastrophic forgetting |
| run_3 | L1-D `reorder_curriculum` (stories interleaved) | 0.925 (E2) | 0 | Sweet spot E2 |
| run_4 | L1-D `reorder_curriculum` (phase semantic cluster) | 0.943 (E4) | 1 | Sweet spot E4; best overall |
| run_5 | L1-C `oversample_cluster` (reasoning ×4) | 0.924 (E3) | 2 | Arithmetic appeared E2; ×4 too high |
| run_6 | L1-C `oversample_cluster` (reasoning ×2) | (fill) | (fill) | |

---

### Step 4 — Build the corpus

```bash
python meta/scripts/build_training_corpus.py \
  --output training/corpus/run_N_[name].txt \
  --report training/corpus/run_N_build_report.txt \
  [flags]
```

**Flag reference:**
- Semantic cluster ordering: `--cluster-sequence training_data/phases/cluster_sequence.txt`
- Reasoning oversample ×N: `--oversample-reasoning N`

Verify: output must end with `All files validated — corpus is clean.`
Do not train on a corpus with skipped files.

---

### Step 5 — Create the report template

Copy the header structure from `training/logs/run_N-1_report.md`.
Save as `training/logs/run_N_report.md`.
Fill in the setup table and motivation section.
Leave all epoch sections as `(fill)`.

---

### Step 6 — Launch training

```bash
nohup python train.py \
  --phase 0 \
  --corpus-file training/corpus/run_N_[name].txt \
  --output core/run_N_[name].pt \
  --resume checkpoints/[base].pt \
  --epochs [3 or 5] \
  --epoch-checkpoints \
  --amp-bf16 \
  > training/logs/run_N_train.log 2>&1 &
```

Monitor for the first epoch checkpoint:
```bash
until [ -f core/run_N_[name]_e1.pt ]; do sleep 60; done
```

---

### Step 7 — Eval every epoch

As soon as each checkpoint file appears:

```bash
CKPT=core/run_N_[name]_eK.pt
python meta/scripts/probe.py --checkpoint "$CKPT" --temperature 0.7 --tokens 120
python eval.py --checkpoint "$CKPT"
```

Record in the report:
- Epoch loss (from training log — may be buffered; fill after next epoch flushes)
- Probe: garbled/12, sentences/12, pronouns/12, negation/12 + notable outputs
- Eval: Raw, Shaped, delta, Loops, Abrupt stops, worst and best shaped outputs

---

### Step 8 — Select the best checkpoint

After all epochs complete:

- Primary criterion: highest **shaped** score.
- Tiebreaker: fewest loops.
- Do not auto-select higher shaped if loops increased significantly — note the trade-off.

Then run this exact sequence (substitute RUN_NAME and BEST_EPOCH):

```bash
RUN_NAME=run_6_oversample_reasoning_x2
BEST_EPOCH=e2

# Copy best to checkpoints/
BEST=core/${RUN_NAME}_${BEST_EPOCH}.pt
DEST=checkpoints/run6_${BEST_EPOCH}.pt
cp "$BEST" "$DEST"

# Confirm copy before deleting anything
ls -lh "$DEST"

# Delete all other epoch checkpoints for this run from core/
find core/ -name "${RUN_NAME}_e*.pt" ! -name "${RUN_NAME}_${BEST_EPOCH}.pt" -delete

# Confirm what remains
ls core/${RUN_NAME}*.pt
```

This is the only safe way to clean up. Never delete by hand — one wrong glob and a base checkpoint is gone.

---

### Step 9 — Fill the report

Complete every `(fill)` in the report:
- All epoch losses (from log)
- Summary table
- Selected checkpoint with reason
- Key observations: what the target metric did, what regressed, what to try next

---

### Step 10 — Decide the next intervention

Answer three questions from the completed report:
1. Did shaped score improve over the previous best?
2. Did the target probe category improve?
3. Did any new failure mode appear?

Write the next run in `todo.md` with: base checkpoint, intervention, one-sentence justification.

---

## Guardrails

**G1 — No run without a read.**
Never choose an intervention without reading the previous report. The report is the source of truth.

**G2 — Shaped is the primary metric.**
Raw improvement without shaped improvement is not success.

**G3 — Probes confirm; evals decide.**
A correct arithmetic answer in the probe is a positive signal, not a success declaration.
The eval shaped score decides whether the checkpoint is promotable.

**G4 — Loop count is a quality floor.**
Loops spreading to new prompts is a regression even if shaped is higher.

**G5 — One intervention, one variable.**
Two simultaneous changes make the next run uninformative.

**G6 — Do not copy-paste from a prior run.**
Build a new corpus, write a new report, verify each epoch freshly.

**G7 — Verify the corpus before training.**
`All files validated — corpus is clean.` is required. Skipped files mean broken training signal.

**G8 — Arithmetic probe is not the only reasoning signal.**
"Two plus two is four" at one temperature does not mean reasoning is fixed.
Test zero, ordinal, and multi-step cases before declaring success.

---

## Related files

- `docs/training_pipeline.md` — corpus layers, content descriptions, training sequence
- `docs/mommy_says_machine.md` — evaluation and targeted correction protocol
- `training/logs/` — per-run reports
- `inventory/allowlist.txt` — content word gate
- `training_data/phases/cluster_sequence.txt` — semantic cluster ordering for run_4+
