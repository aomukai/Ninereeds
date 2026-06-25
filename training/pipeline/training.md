# Ninereeds Training Reference

Combines the training harness design and the step-by-step training manual.
Single source of truth for how to run, evaluate, and improve the model.

Last updated: 2026-06-21

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
- **Shaped score is a primary quantitative metric, but brain_map is evaluated first.**
  The prompt shaper is part of the live inference pipeline. A checkpoint that scores well raw
  but poorly shaped is not useful. However, two checkpoints with near-identical shaped scores
  cannot be distinguished by eval alone — brain_map cluster structure is the tiebreaker and
  must always be checked before selecting a winner.
- **E2–E4 sweet spots are likely an architecture property.** E1 is always Adam warmup noise.
  E5+ is always memorisation overfit. The exact sweet spot shifts with intervention intensity:
  milder changes peak earlier (E2), more disruptive changes peak later (E4).
- **EDJC rotation improves JP/ZH circuits.** Cycling language order across corpus files
  (EDJC/DJCE/JCED/CEDJ) prevents EN/DE from always occupying the first (highest Hebbian
  weight) position. Confirmed in C15: arithmetic_jp at the language-block stage jumped from
  0.912 (C14c peak, after 4 subsequent blocks) to 0.987 at E2 of just the first block.
- **Arithmetic saturation rule.** Never run a standalone arithmetic block with fewer than
  ~100 files × 3 epochs. C14c showed 20 arithmetic-only files collapsed shaped from
  0.934 → 0.863. Arithmetic signal must be embedded in a broader corpus mix.
- **train.py reads --corpus-file as raw bytes.** Passing a manifest file path trains on
  file-path strings, not content. Always build a flat corpus with build_training_corpus.py
  first and pass the output .txt file.

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

#### Priority order

**Highest to lowest — this order is non-negotiable:**

1. **brain_map** — cluster structure and hub μ per category (language.jsonl + thinking.jsonl)
2. **shaped score** (eval.py) — primary quantitative signal
3. **raw score** (eval.py) — secondary; useful for diagnosing shaper interaction
4. **training loss** — dead last; has very little to do with what we are testing for

Brain_map is the MRI of the model. Loss is the fit to next-token prediction — not the goal.
Two checkpoints with near-identical shaped scores (e.g. 0.989 vs 0.990) cannot be
distinguished by eval alone; brain_map cluster structure is the tiebreaker.

**Do not select a block winner without brain_map evidence.** Shaped score selects among
candidates with similar brain_map profiles, not before it.

#### Tools

```bash
# Brain map — cluster structure; run FIRST after each block completes
python meta/scripts/brain_map.py probe \
  --checkpoint $CKPT \
  --probes training/corpus_admin/probe_sets/language.jsonl \
  --name ${RUN}_language
python meta/scripts/brain_map.py probe \
  --checkpoint $CKPT \
  --probes training/corpus_admin/probe_sets/thinking.jsonl \
  --name ${RUN}_thinking
python meta/scripts/brain_map.py hubs  --name ${RUN}_language --threshold 0.7
python meta/scripts/brain_map.py graph --name ${RUN}_language
python meta/scripts/brain_map.py hubs  --name ${RUN}_thinking --threshold 0.7
python meta/scripts/brain_map.py graph --name ${RUN}_thinking
# HTML graphs: training/logs/brain_maps/${RUN}_{language,thinking}_graph.html

# Eval — shaped and raw scores (run after brain_map)
python eval.py --checkpoint $CKPT

# Probes — qualitative output quality across 12 prompt categories
python meta/scripts/probe.py --checkpoint $CKPT --temperature 0.7 --tokens 120
```

Run all three after every epoch checkpoint, immediately when the checkpoint file appears.
Do not skip any tool. Do not defer eval to after the run completes.

#### Shaped score

The eval produces two scores: **raw** and **shaped**.

- **Raw**: average score of direct model completions.
- **Shaped**: average score after the prompt shaper routes each prompt to the appropriate
  format before inference. The shaper is part of the live inference pipeline.

**Shaped is the primary quantitative metric.** A checkpoint with raw 0.921 / shaped 0.892
(run_3 E3) is worse than one with raw 0.898 / shaped 0.925 (run_3 E2), despite better raw.

A strongly negative shaped delta (shaped << raw) means the model has learned content
patterns the shaper penalises — typically language-register bleed or format mismatch.

#### Training loss

Loss can be omitted from epoch summaries unless it shows a clear anomaly (sudden spike =
possible training bug). Do not use loss to rank checkpoints or select winners.

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
- **GPU assignment:** GPU 0 is the training card (always free after training finishes). GPU 1
  is the daily-use card — eval on GPU 1 may run on CPU if desktop workload is present.
  Always use `CUDA_VISIBLE_DEVICES=0` for eval.
- **Memory-constrained training** (when desktop apps consume most VRAM): add
  `--batch-size 1 --grad-accum-steps 2 --adam8bit` and set env
  `PYTORCH_ALLOC_CONF=expandable_segments:True`. Reduces peak VRAM by ~350 MB.
  bitsandbytes 0.49.2 is installed.
- **Automated pipeline:** `meta/scripts/c15_pipeline.py` runs a full block sequence
  (train → eval → brain_map → pick winner → launch next) unattended. See
  `training/docs/pipeline.md` for the automation design and planned `campaign_runner.py`.

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

### Empirical findings and open questions

Maintained in `docs/curriculum_topology.md` — that document is the authoritative research
reference and is kept more current than this file. Key rules extracted here for quick
reference during a session:

- **E1 winner for focused blocks; E2 winner for full-curriculum blocks.** Blocks with <500
  files (arithmetic, reasoning) saturate fast — E1 is typically the peak. Large full-curriculum
  blocks (42k files) peak at E2. E3 regresses in every observed case.
- **Vignettes compress arithmetic circuits.** Each epoch of vignettes training costs ~0.08
  arith_jp after-hub. Run 1 epoch only; do not run 3.
- **Oversample dosing:** start at ×2; ×4 causes cross-domain bleed. If ×2 fails, the problem
  is retrieval framing, not weight — use `teacher_student_drill`.
- **EDJC rotation** eliminates EN/DE positional advantage. Always use for multilingual blocks.
- See `docs/curriculum_topology.md` for full campaign history, failure modes, and open questions.

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

**Intervention history (update each campaign):**

| Campaign | Intervention | Peak shaped | Loops | Notes |
|---|---|---|---|---|
| 1 | baseline | — | — | |
| 2 | story fine-tune (separate) | 0.922 | — | E1 catastrophic forgetting |
| 3 | L1-D `reorder_curriculum` (stories interleaved) | 0.925 (E2) | 0 | Sweet spot E2 |
| 4 | L1-D `reorder_curriculum` (phase semantic cluster) | 0.943 (E4) | 1 | Sweet spot E4; best overall |
| 5 | L1-C `oversample_cluster` (reasoning ×4) | 0.924 (E3) | 2 | Arithmetic appeared E2; ×4 too high |
| 6–12 | (see reports_1-12/) | — | — | |
| 13 | dependency-ordered curriculum (phases A–B + teaching block), 25M, block eval | 0.925 | 0 | First block-based campaign; 5-folder corpus structure |
| 14a | Language core (EDJC rotation, full multilingual eval 72 prompts) | 0.958 (E2) | 0 | EDJC rotation introduced; E2 winner |
| 14b | Arithmetic bridge + grounded stories | 0.976 (E1) | 0 | E1 winner; grounded stories dominate later epochs |
| 14c | Reasoning/arithB + vignettes + education | 0.943 → 0.934 | 0 | Arithmetic standalone block (20 files) collapsed shaped; saturation rule established |
| 15 B1 | Language core retrain on EDJC-rotated full curriculum | 0.958 (E2) | 0 | arith_jp 0.987 at E2 — highest ever at language-block stage |
| 15 B2 | Arith + grounded stories | 0.976 (E1) | 0 | E1 winner pattern for focused blocks confirmed |
| 15 B3 | Reasoning/arithB (73 files) | 0.941 (E1) | 0 | E1 winner; rule_application spike at E2 (0.921) but cost arith_jp |
| 15 B4–5 | Vignettes + Education | (in progress) | — | Pipeline running autonomously |

---

### Step 4 — Build the phase corpus

Each campaign trains one phase at a time.  Build a corpus chunk from the JSONL order file:

```bash
CAMPAIGN=13
PHASE=A   # A, B, C, D, E, grammar, bridge, grounded_stories

python meta/scripts/build_training_corpus.py \
  --order-file training/training_order/phase_${PHASE}_order.jsonl \
  --output training/corpus/campaign_${CAMPAIGN}_phase_${PHASE}.txt \
  --report training/corpus/campaign_${CAMPAIGN}_phase_${PHASE}_report.txt
```

Verify: output must end with `All files validated — corpus is clean.`
Do not train on a corpus with skipped files.

**To modify training order:** edit the JSONL file directly — reorder lines, set
`"probe_after": true` at checkpoints, add/remove units.  Do not regenerate from the
curriculum graph unless explicitly starting a new ordering experiment.

#### Campaign 14 — teaching block corpus

Campaign 14 introduces a third corpus chunk between Phase B and the probe checkpoint:
the teaching block (domain-sorted teaching stories interleaved with boolean, triplets,
and grounded stories).  The order manifest is a plain `.txt` file — the builder detects
the extension and uses the text-format reader automatically.

```bash
CAMPAIGN=14

# Phase A (existing JSONL order)
python meta/scripts/build_training_corpus.py \
  --order-file training/training_order/phase_A_order.jsonl \
  --output training/corpus/campaign_${CAMPAIGN}_phase_A.txt \
  --report training/corpus/campaign_${CAMPAIGN}_phase_A_report.txt

# Phase B (existing JSONL order)
python meta/scripts/build_training_corpus.py \
  --order-file training/training_order/phase_B_order.jsonl \
  --output training/corpus/campaign_${CAMPAIGN}_phase_B.txt \
  --report training/corpus/campaign_${CAMPAIGN}_phase_B_report.txt

# Teaching block — generated by meta/scripts/build_teaching_order.py
python meta/scripts/build_training_corpus.py \
  --order-file training/corpus_admin/campaign14_order.txt \
  --output training/corpus/campaign_${CAMPAIGN}_teaching.txt \
  --report training/corpus/campaign_${CAMPAIGN}_teaching_report.txt

# Concatenate all three into the full campaign corpus
cat training/corpus/campaign_${CAMPAIGN}_phase_A.txt \
    training/corpus/campaign_${CAMPAIGN}_phase_B.txt \
    training/corpus/campaign_${CAMPAIGN}_teaching.txt \
    > training/corpus/campaign_${CAMPAIGN}_full.txt
```

All three verify steps must return `All files validated — corpus is clean.` before
concatenation.  Do not train on a concatenated corpus that has skipped files in any chunk.

**Teaching block order:** `training/corpus_admin/campaign14_order.txt` — 10,034 files,
8 domain blocks (concrete → action → social → time → emotions → cognitive → abstract → math).
To regenerate or adjust interleaving ratios:
```bash
python meta/scripts/build_teaching_order.py stats     # show block distribution
python meta/scripts/build_teaching_order.py interleave --bool-stride 6 --triplet-stride 4 --grounded-stride 26
```

**Training flag:** use `--no-shuffle` for the teaching block run to preserve domain ordering.

---

### Step 5 — Create the phase report

Reports live in `training/logs/campaign_N_reports/`.
Name: `NN_phase_X.md` where NN is a zero-padded sequence number within the campaign.

```
training/logs/campaign_13_reports/
  01_phase_A.md
  02_phase_B.md
  03_phase_C.md
  ...
```

Copy the header structure from the previous report.  Fill in the setup table and
motivation section.  Leave all epoch sections as `(fill)`.

---

### Step 6 — Launch training

```bash
CAMPAIGN=13
PHASE=A

nohup python train.py \
  --phase 0 \
  --corpus-file training/corpus/campaign_${CAMPAIGN}_phase_${PHASE}.txt \
  --output core/campaign_${CAMPAIGN}_phase_${PHASE}.pt \
  --resume checkpoints/[base].pt \
  \
  --epochs 3 \
  --epoch-checkpoints \
  --amp-bf16 \
  > training/logs/campaign_${CAMPAIGN}_reports/phase_${PHASE}_train.log 2>&1 &
```

Monitor for the first epoch checkpoint:
```bash
until [ -f core/campaign_${CAMPAIGN}_phase_${PHASE}_e1.pt ]; do sleep 60; done
```

Scale flags: no flag = 25M default (crash-test), `--scale-150m` (promoted after 25M validates), `--scale-600m`.

---

### Step 7 — Eval every epoch

As soon as each checkpoint file appears. Run **brain_map first** — it is the primary criterion
for winner selection. Eval and probe are secondary.

```bash
CKPT=core/campaign_${CAMPAIGN}_phase_${PHASE}_eK.pt
NAME=campaign${CAMPAIGN}_phase${PHASE}_eK

# 1. Brain map (PRIMARY — run first)
python meta/scripts/brain_map.py probe \
  --checkpoint "$CKPT" \
  --probes training/corpus_admin/probe_sets/language.jsonl \
  --name ${NAME}_language
python meta/scripts/brain_map.py hubs  --name ${NAME}_language --threshold 0.7
python meta/scripts/brain_map.py graph --name ${NAME}_language

python meta/scripts/brain_map.py probe \
  --checkpoint "$CKPT" \
  --probes training/corpus_admin/probe_sets/thinking.jsonl \
  --name ${NAME}_thinking
python meta/scripts/brain_map.py hubs  --name ${NAME}_thinking --threshold 0.7
python meta/scripts/brain_map.py graph --name ${NAME}_thinking
# HTML graphs: training/logs/brain_maps/${NAME}_{language,thinking}_graph.html

# 2. Eval (shaped + raw scores)
python eval.py --checkpoint "$CKPT"

# 3. Probe (qualitative output samples — optional, for spot-checking)
python meta/scripts/probe.py --checkpoint "$CKPT" --temperature 0.7 --tokens 120
```

Use `CUDA_VISIBLE_DEVICES=0` for eval — GPU 0 is always free after training finishes.
Do not use GPU 1 (daily-use card, may have desktop workload).

Record in the report:
- Epoch loss (from training log — may be buffered; fill after next epoch flushes)
- Brain map: arithmetic_jp after-hub, arithmetic_zh after-hub, spatial after-hub, contrastive after-hub
- Eval: Raw, Shaped, per-language breakdown (EN/DE/JP/ZH), Loops, Abrupt stops
- Probe: garbled/12, sentences/12, pronouns/12, negation/12 + notable outputs (optional)

---

### Step 8 — Select the best checkpoint

After all epochs complete. **Do not pick a winner without reviewing the brain_map.**

Priority order (non-negotiable — same as Part 1 evaluation doctrine):
1. **arithmetic_jp after-hub** (thinking brain_map) — primary circuit health signal.
   Higher = more dedicated JP arithmetic circuits, less hub-dependency.
2. **Shaped score** — tiebreaker when arithmetic_jp is within 0.005 across candidates.
3. **Fewest loops** — quality floor. Do not promote a checkpoint with loops ≥ 4.
4. **Training loss** — never used for winner selection.

Scan the full thinking and language hub tables (all 14 + 16 categories) before deciding.
A single-metric win (e.g. rule_application spike at E2) is only valid if it does not cost
arithmetic_jp, shaped, or major language circuits. Document the trade-off explicitly if one exists.

Then run this exact sequence (substitute CAMPAIGN, PHASE, BEST_EPOCH):

```bash
CAMPAIGN=13
PHASE=A
BEST_EPOCH=e2

RUN_NAME=campaign_${CAMPAIGN}_phase_${PHASE}

# Copy best to checkpoints/
BEST=core/${RUN_NAME}_${BEST_EPOCH}.pt
DEST=checkpoints/campaign${CAMPAIGN}_phase${PHASE}_${BEST_EPOCH}.pt
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

Write the next phase or campaign in `todo.md` with: base checkpoint, phase, one-sentence justification.
A campaign ends when all planned phases are complete or a regression warrants stopping and re-designing.

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
