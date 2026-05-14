# BDH Training Harness Design

Defines the offline training, evaluation, branching, and merge harness for the BDH system.

Last updated: 2026-05-15

---

## Purpose and doctrine

The harness exists to improve the model through explicit, auditable interventions
rather than opaque self-modification. Its target: a coherent BDH-based conversational
model with broad, shallow knowledge, deeper capability deferred to Skill LoRA, and
continued growth through a controlled offline Dream LoRA process.

Core doctrine:
- Goal-specific capability is developed on side branches and integrated into mainline
  through a supervised merge pipeline.
- Transparency over opacity. One bounded round at a time. One major intervention per round.
- Verifier-gated teacher output. Human oversight at the strategic level.
- Branching and merging is not a licence for open-ended population search —
  it is a controlled extension of the same philosophy: local search around explicit
  hypotheses, narrow promotion rules, bias toward reversibility.

BDH-specific note: the BDH paper reports that BDH-GPU can be scaled by varying the
number of neurons and demonstrates a direct merge (concatenate neuron-dimension tensors,
average shared tensors) where the merged model retained meaningful capabilities and
improved quickly with a small post-merge training pass. This makes branch–specialise–
integrate a sensible design pattern for this architecture. Raw merges still require a
repair phase before mainline promotion.

---

## Roles and decision boundaries

Three roles:

**Orchestrator** — policy owner. Proposes the next action; owns the intervention
question (what to do inside the current campaign) and the integration question
(whether a branch should remain a specialist, stay as branch champion, or merge
into mainline). Does not execute.

**Executor** — bounded worker. Runs one round and stops. May materialise a branch,
compare branches, produce a sandbox merge, run a repair round, or write reports.
Does not invent policy, widen scope, or silently promote anything.

**Verifier** — mandatory for: student-facing content, evaluation judgments that affect
promotion, draft training data, merge promotion decisions. Validates lineage completeness,
merge-plan correctness, evaluation integrity, and whether a proposed promotion package
supports the decision being claimed.

---

## Bias-Balancing Circuit Breaker

A deliberately simple anti-dominance mechanism to prevent either the Orchestrator or
Executor from becoming the de facto sole authority during unattended operation.

**Protocol:**
1. Orchestrator proposes the next action.
2. Executor may accept or raise a technical objection.
3. Objections must cite concrete artefacts: `metrics.json`, `worker_report.json`,
   `decision.json`, or evaluation gate failures.
4. Each side is limited to two evidence-bearing turns.
5. If no agreement is reached, a deterministic parity rule applies:
   - even global round → Orchestrator wins
   - odd global round → Executor wins

**Scope constraints (critical):**
The circuit breaker may only resolve decisions where both options are already valid
under harness policy. It must never override: verifier failures, Tier 1 evaluation
failures, promotion gate failures, missing or invalid artefacts, invalid lineage /
merge plan, or out-of-scope data generation.

**Audit:** every arbitration event is logged in `ROUND_STATE.json`:
```json
{
  "arbitration_applied": true,
  "tie_break_winner": "orchestrator",
  "global_round": 42,
  "losing_objection": "Executor flagged insufficient retention evidence",
  "policy_gates_passed": true
}
```

---

## State model

Three nested units:

**Round** — atomic unit. One major change only. One hour cadence.

**Campaign** — persistent local-search unit. Cluster- or hypothesis-centred container
with a parent checkpoint, allowed interventions, stop conditions, and outcome
classification. Gives the system memory and local research continuity.

**Frontier** — the small live set of branches a campaign is currently allowed to
manipulate. At most three live candidates per campaign:
- **Champion:** best current branch or merge path on the campaign objective.
- **Challenger:** most plausible alternative from a different intervention or merge recipe.
- **Explorer:** reserved for deliberate diversity when progress plateaus
  (lower-kinship merge parent or materially different recipe).

**Branch state classes:**
`mainline`, `campaign_branch`, `merge_candidate`, `archive_promising`,
`archive_failed_but_informative`, `reverted_snapshot`.

**Branch decisions:**
`keep_as_mainline`, `keep_as_branch_champion`, `archive_promising`,
`archive_failed_but_informative`, `revert`, `request_more_data`.

All merge-eligible branches must originate from the current mainline or from an
explicitly named merge base. Ancestry, training schedule, optimiser regime, steps,
data ratio, and target cluster are part of branch identity. Unknown fields weaken
a branch as a merge parent.

---

## Intervention registry

### Layer 1 — base interventions

| Intervention | Description |
|---|---|
| `train_longer` | Extend the current training run |
| `teacher_student_drill` | Targeted drill on a failure cluster |
| `oversample_cluster` | Increase weight of a failing concept group |
| `reorder_curriculum` | Change the ordering of the training sequence |
| `add_contrastive_pairs` | Add pairs that contrast a failing concept with a nearby correct one |
| `simplify_wording` | Reduce complexity in the corpus for a struggling concept |
| `verify_teacher_output` | Gate: run the verifier on a batch before it enters training |
| `request_more_data` | Human escalation: the current campaign is exhausted |

### Layer 2 — branching and retention

| Intervention | Description |
|---|---|
| `compare_branch` | Compare two branches on the campaign objective |
| `merge_candidate` | Propose and evaluate a merge of two branches |
| `retention_probe` | Test whether knowledge survives a distractor sequence |

### Layer 3 — merge lifecycle

| Intervention | Description |
|---|---|
| `premerge_align` | Weight alignment before merging (e.g., Git Re-Basin) when geometric misalignment is the issue |
| `postmerge_repair` | Brief joint rehearsal, calibration, or corrective LoRA after a merge that passes most evaluations but shows residual bias or calibration drift |

### Layer 4 — corpus and language layer interventions

These are new intervention types motivated by the multilingual, multi-layer corpus.

| Intervention | Description |
|---|---|
| `language_isolate` | Run evaluation on a single language layer (e.g., JP only) to isolate cross-language interference without changing training data |
| `layer_gate_probe` | Test whether a newly introduced corpus layer is degrading performance on an earlier layer (e.g., does adding lang_5 erode lang_3 precision?) |
| `register_correction` | Targeted retraining or contrastive drilling on a specific language register (e.g., DE drifting toward academic register instead of textbook) |
| `localization_audit` | Verify that the model's multilingual outputs maintain semantic fidelity — objects, actors, and counts from EN must survive into DE/JP/ZH without substitution or drift |
| `allowlist_gate` | Halt corpus expansion if auditing reveals that a new story or lang file has introduced vocabulary outside the allowlist; repair before reintroducing into training |
| `cross_layer_probe` | Test whether the model correctly applies knowledge across corpus layers — e.g., does it use lang question-answer training when handling phase-style questions? |
| `philosophy_register_probe` | Specific to the philosophy corpus: verify that the である体 / Schulbuch / written Chinese registers are stable in NINEREEDS turns and that USER turns remain conversational |

---

## Merge and recipe policy

### Parent selection

Default: homologous merging only — same BDH family, same tokenizer, compatible tensor
topology, preferably a shared checkpoint ancestor.

The orchestrator carries a **mergeability budget** for every branch:
divergence from base, fine-tuning depth, learning-rate regime, data ratio, rehearsal
exposure, interference history.

Branches intended for later integration should be useful specialists, but not trained
so far or so idiosyncratically that they stop being merge-friendly.

### Recipe escalation

1. **Soup-style averaging or task arithmetic** — for close siblings differing mainly by
   light specialisation or hyperparameter path.
2. **TIES or DARE** — if interference is likely (sign conflict, redundant low-magnitude
   changes, or more than two source experts).
3. **`premerge_align` + Git Re-Basin** — if the issue is geometric misalignment rather
   than task conflict.
4. **`postmerge_repair`** — if the merged checkpoint passes most evaluations but shows
   residual bias or calibration drift.

### BDH-specific structural merging

When the goal is capacity expansion or composition of disjoint specialists kept close
to a common base:
- concatenate tensors along the neuron dimension
- average the shared tensors

Do not confuse "architecture-native" with "safe to promote." The paper's own experiment
showed asymmetric degradation after raw merge. A repair stage (brief joint rehearsal,
calibration, or temporary corrective LoRA) is required before mainline promotion.

### Bounded recipe search

Legitimate search dimensions: parent pair or set, recipe family, coefficients,
sparsity density, alignment choice, repair budget, stopping rule.

The frontier stays small. Every merge proposal must be attached to a campaign or
explicit integration objective. High kinship among surviving candidates is a
convergence signal, not an excuse to keep generating near-identical descendants.

---

## Lineage tracking

### Branch registry fields

```json
{
  "branch_id": "B014-SOCROLE",
  "parent_branch_id": "B009-SOCROLE",
  "base_checkpoint": "ckpt_001",
  "generation_depth": 4,
  "campaign_id": "C003-SOCROLE",
  "ancestor_chain": ["mainline_001", "B002", "B006", "B009"],
  "lineage_family": "SOCROLE_A"
}
```

### Merge plan lineage evaluation

```json
{
  "lineage_compatibility": {
    "common_ancestor": "B009-SOCROLE",
    "generations_since_common_ancestor": 1,
    "recent_common_ancestor_flag": true,
    "structural_redundancy_risk": "high",
    "expected_merge_value": "low"
  }
}
```

Rules:
- `generations_since_common_ancestor <= 2` → likely redundant; low merge value
- distant lineage → higher diversity → higher value, but higher risk

### Lineage metrics

```json
{
  "lineage_metrics": {
    "generation_depth": 4,
    "generations_since_common_ancestor": 1,
    "lineage_diversity_score": 0.18
  }
}
```

`lineage_diversity_score` is a normalized measure of ancestry divergence.
Low → high overlap → low merge value. High → meaningful diversity → integration candidate.

### Merge decision policy

Three axes: merge risk (regression likelihood), merge value (capability gain),
lineage diversity (whether the merge is worth attempting).

| Diversity | Value | Decision |
|---|---|---|
| Low | Low | Reject or archive |
| Low | Specific repair goal | Allow (repair merge only) |
| High | Low risk | Strong merge candidate |
| High | High risk | Sandbox merge + strict evaluation |

**Default constraint:** do not merge branches with recent common ancestry unless
the merge is explicitly classified as a repair or reconciliation step.

---

## Evaluation and promotion policy

### Tiered evaluation gates

**Tier 1 (Cheap Gate):** syntax stability, formatting correctness, checkpoint
loadability, blatant output corruption.

**Tier 2 (Seismic Gate):** concept integrity, reasoning consistency, grounding,
behavioural health.

**Retention Anchor:** retention is a first-class requirement, measured through delayed
recall and distraction robustness. A model that passes immediately but loses knowledge
after a distractor sequence is classified as "excited" rather than "integrated" and
fails promotion.

**Language Consistency Gate** (new): for any checkpoint trained on multilingual corpus
layers, evaluate across all four languages (EN/DE/JP/ZH). Failures in one language
layer do not automatically fail other layers but must be logged and treated as a
`language_isolate` trigger before promotion.

### Promotion sequence

A branch moves to mainline only if it clears four comparisons:

1. **Target improvement:** branch vs. parent on the specific campaign goal.
2. **Merge integrity:** sandbox merge vs. winning branch (did the merge erase the gain?).
3. **Global safety:** sandbox merge vs. mainline on the global regression suite.
4. **Retention probe:** merged model holds knowledge across a distractor sequence.

If "almost ready" with minor residuals: one bounded `postmerge_repair` round is allowed.
If that fails: `archive_promising`, not promotion.

### ROUND_STATE.json tracking fields

```json
{
  "consensus_rounds": 1,
  "arbitration_applied": false,
  "tie_break_winner": null,
  "rejection_reason": null,
  "language_layers_evaluated": ["EN", "DE", "JP", "ZH"],
  "layer_gate_probe_result": "pass"
}
```

---

## Artefacts and logs

### Round artefacts

Always required: `plan.md`, `summary.md`, `metrics.json`, `decision.json`,
`worker_report.json`.

When a round mutates or evaluates a checkpoint: also emit `branch_card.json`.

When a round performs or evaluates a merge: also emit `merge_plan.json`,
`merge_metrics.json`, `lineage.json`, `promotion_review.json`.

Conditional: `verifier_report.json`, `draft_data_request.json`,
`draft_training_data.md`, `notes.md`.

### branch_card.json fields

Base checkpoint, training objective, target cluster, data provenance, optimiser regime,
steps, learning-rate schedule, rehearsal exposure, verifier status, mergeability budget,
**corpus layers included in training** (e.g., `["lang_1", "lang_2", "phases_1_3"]`).

The corpus layers field is new and necessary: a branch trained on lang_1–3 + phases
has a different capability profile than one trained on the full corpus, and this must
be explicit in the merge plan.

### merge_plan.json fields

Parent hashes, common ancestor, kinship summary, chosen recipe, coefficients,
sparsity/density settings, alignment transform if any, repair allowance, exact
evaluation suites required for promotion, **language evaluation scope**.

### Logs

- `round_index.jsonl`
- `intervention_history.jsonl`
- `emergency_requests.jsonl`
- `campaign_index.jsonl`
- `branch_registry.jsonl`
- `merge_registry.jsonl`
- `retention_history.jsonl`

`merge_registry.jsonl` is especially important: the orchestrator will otherwise lose
the empirical history of which parent combinations, recipes, sparsity levels, and
repair budgets produced useful descendants.

---

## Cadence

One round per hour. Campaign context persists across rounds.

Merge work may span several rounds: screening in one, sandbox materialisation in the
next, repair in a third. But each round makes one major change only.

If the corpus gate remains closed: stay in dry-run mode. Compare branches, run
verifier checks, plan merges, simulate promotion logic, and draft data requests.
Do not mutate mainline until corpus state allows live training.

---

## Related files

- `docs/training_pipeline.md` — corpus layers and training sequence
- `docs/mommy_says_machine.md` — evaluation and targeted correction protocol
- `inventory/allowlist.txt` — content word gate
- `training/` — training harness implementation
