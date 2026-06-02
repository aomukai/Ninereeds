# Brain Map — Activation Atlas and Modular Training

## Core idea

Ninereeds' activation sparsity (inherited from the BDH-GPU architecture) means that
different prompts activate largely non-overlapping neuron subsets. This makes it possible
to *map* the model's internal activation geometry — and, if clusters prove causally valid,
potentially to *transplant* specific capabilities between checkpoints.

The model is treated less like a monolithic function approximator and more like a living
circuit atlas — closer to modular cortical recruitment than transformer-style feature
superposition.

## Current status: v1 scanner completed, v2 in design (2026-06-02)

`meta/scripts/brain_map.py` records `xy_sparse` (Hebbian co-firing signal) at the last
prompt-token position across all layers. A first pass on the C13 winner ran 180 probes
across 13 categories. Results and their correct interpretation are in the section below.

**The scanner is real and useful as an activation-geometry diagnostic.**
**It is not yet reliable enough to claim semantic cluster identity without further controls.**

## What the v1 scanner measures — and what it does not

The script captures `xy_sparse` at the last token of the prompt, flattened to a vector,
then computes cosine similarity across probes. This is a meaningful internal signal —
different prompt families, languages, formats, and grammatical constructions do produce
different co-firing patterns.

**What it does not measure:** understanding, output competence, or causal concept
ownership. A co-firing state at the end of the prompt is not proof that the model has
formed a semantic concept. Lesion testing (Phase 3 below) is required before any cluster
can be trusted causally.

**The critical confound:** prompt template. If all emotion probes use "What does X look
like?" and all cognitive probes use "What does it mean to be X?", high intra-category
similarity may be measuring prompt-shell consistency rather than semantic cluster
formation. v1 did not control for this.

## v1 findings — C13 winner (correctly interpreted)

**Activation geometry:** different prompt families produce detectably different co-firing
patterns. The scanner works as a family-level discriminator.

**Hub structure:** 289 neurons (0.15%) fire across ≥70% of probe categories. Head 1
across layers is the dominant routing channel. These are **high-breadth co-firing
candidates**, not confirmed routing hubs until lesion tests exist.

**Category-exclusive dimensions:** neurons firing in exactly one probe category. These
are **category-exclusive co-firing dimensions in this probe set**, not confirmed semantic
neurons.

| Category | Exclusive dimensions |
|---|---|
| grammar_dative (aggregated) | 2,083 |
| grammar_v2 | 1,458 |
| phase_b | 1,332 |
| phase_a | 651 |
| emotion | 454 |
| arithmetic | 247 |
| cognitive | 85 |

**Dative finding (corrected):** aggregate dative similarity = 0.482 was mixing
constructions. Split by construction: über-static ≈ 0.908, in-static ≈ 0.989,
mit-companion ≈ 0.819. The scanner reveals that dative should not be treated as one
category — construction-level probes are needed.

**Multilingual finding (corrected):** EN and DE within-language template similarity are
near-identical (0.989 / 0.985), but this is template consistency, not cross-language
concept alignment. Actual EN↔DE same-concept vs different-concept cosine similarity
is ~0.746 vs ~0.744 — essentially no concept-alignment signal in v1. The scanner
currently detects language/template manifolds, not cross-language concept identity.

**"87% silent" (corrected):** means "not activated by this 180-probe battery." It does
not mean those neurons are unused globally, and it does not rule out capacity-related
explanations for B/D/E failure. The xy_sparse capture is also stricter than raw
activation sparsity (it is the product of x_sparse and y_sparse), so observed sparsity
is lower than the architectural 3–5% figure.

**Emotion/cognitive clusters (downgraded):** intra-category similarity for emotion
(0.835) and cognitive (0.976) may reflect prompt-shell consistency rather than semantic
cluster formation. Emotion's margin over Phase A (0.835 vs 0.819 cross-similarity) is
too thin to be meaningful. Cognitive's 0.976 is almost certainly the identical sentence
frame for all 15 probes. These are **not confirmed as semantic clusters.**

## Terminology going forward

To prevent conclusions from outrunning data, use these terms:

| Old term | Correct term |
|---|---|
| Semantic neurons | Category-exclusive co-firing dimensions (in this probe set) |
| Routing hubs | High-breadth co-firing candidates |
| Silent neurons | Not activated by this probe battery |
| Semantic cluster | Activation-geometry family (template controls pending) |

## v2 probe design requirements

Before using the scanner to steer curriculum decisions, each probe needs:

- `concept_id` — the concept being tested
- `template_id` — which question frame is used
- `language` — EN / DE / JP / ZH
- `construction_id` — for grammar probes, which specific construction
- `source_corpus` — which corpus the concept came from
- `expected_behavior` — what a correct output looks like

**Negative controls required:** nonce words in the same templates; known-untrained words;
same template with unrelated concepts; same concept across multiple templates.

**Template crossover test (cheapest first):** run the same concept through two different
question frames. If the activation vectors converge → evidence for semantic cluster.
If they diverge → template-shell effect. This can be added to `brain_map.py` immediately.

**Grammar probes must be split by construction:** `dative_über_static`,
`dative_in_static`, `dative_mit_companion`, `accusative_in_motion`, `dative_recipient`,
etc. Never aggregate case categories.

**Output scoring must accompany activations:** a cluster is only meaningful if it
correlates with correct, incorrect, looping, or garbled behavior. The probe battery
and the competency probe catalogue (`docs/probe_catalogue.md`) must be run together.

## Plan

### Phase 1 — Activation-geometry scan (v1 complete)

`meta/scripts/brain_map.py` implements this. Outputs: `tmp/brain_map_activations.npz`,
`tmp/brain_map_probes.jsonl`, `tmp/brain_map_similarity.png`, `tmp/brain_map_scatter.png`,
`tmp/brain_map_hubs.json`, `tmp/brain_map_similarity_nohubs.png`.

Add `--name` flag before multi-checkpoint comparison so files don't overwrite each other.

### Phase 1b — Template crossover and negative controls (v2, next)

Extend the probe set with:
- Same concept, multiple templates
- Nonce/untrained words in same templates
- Grammar probes split by construction
- Output scores alongside activations

Until Phase 1b is complete, all cluster findings from v1 are **activation-geometry
diagnostics**, not semantic maps.

### Phase 2 — Atlas reproducibility and cluster drift

Run brain map on:
- `checkpoints/c13_phaseA_winner.pt` (earlier checkpoint)
- Multiple seeds of `checkpoints/c13_Phase_C_winner.pt`

Compare cluster *signatures* (centroid similarity, co-firing overlap, probe coverage)
— not raw neuron IDs. If signatures are unstable across seeds, cluster-based
interventions cannot be trusted. This is a prerequisite for Phase 3.

### Phase 3 — Delta tracking (curriculum diagnostics)

Before and after a targeted training intervention:
- Run the full probe pass on both checkpoints
- Diff activation maps using cluster signatures, not raw neuron IDs

### Phase 2 — Delta tracking (curriculum diagnostics)

Before and after a targeted training intervention (e.g. dative case specialist run):
- Run the full probe pass on both checkpoints.
- Diff activation maps using cluster signatures, not raw neuron IDs.
- New or shifted clusters = what the training actually learned.
- Stable clusters = what was preserved.
- Regressed clusters = acceptable collateral if not the target.

This provides measurable internal curriculum diagnostics — did the model truly learn,
memorize, overwrite, generalize, or create competing circuits? Most LLM training lacks
this. Phase 2 makes it possible to answer those questions directly.

### Phase 3 — Lesion testing (causal validation)

Correlation ("this cluster lights up for dative") is not causation. Before trusting a
transplant, validate causally:

1. Identify candidate cluster.
2. Temporarily silence it (zero activations or zero weights in the cluster's neurons).
3. Run the evaluation battery.
4. Measure capability degradation.
5. Restore and repeat for other candidates.

Degradation proportional to cluster size and specificity = causal evidence the cluster
carries the capability. This becomes the gating test before any transplant attempt.

### Phase 4 — Targeted transplantation

Once a cluster is identified and causally validated:
- Compute the weight delta: `Δ = checkpoint_specialist − checkpoint_base`.
- Apply a scaled delta to the base: `base + α * Δ`.
- α may need tuning per specialist — start at 0.5.
- Re-run probes to confirm target cluster transferred and regressions are bounded.

This is task arithmetic adapted for sparse Hebbian weight structure.

**Interference risk:** even sparse systems can interfere through shared routing neurons,
normalization effects, homeostatic balancing, or overlapping prerequisite abstractions.
The odds are better than with dense models, but interference must be measured, not assumed
away. Monitor routing clusters carefully across transplants.

### Phase 5 — Specialist composition

Train multiple specialists on the solid base:
- Grammar specialist (ordered grammar corpus, dative/accusative/genitive)
- Reasoning specialist (reasoning + maths corpus)
- JP naturalness specialist (repaired JP phase corpus)
- ZH specialist
- Spatial relations specialist

Extract deltas from each. Compose onto the base with tuned α per specialist.
Validate each addition with probes and lesion tests before adding the next.

## Visualizer reference

**https://github.com/krychu/bdh**

Already implements BDH-GPU neuron dynamics visualization:
- Layer-by-layer activation GIFs
- Sparsity metrics per layer
- Signal flow through learned circuits

Adapt to produce: static cluster map, before/after activation movies across curriculum
stages and specialist merges, regression event markers.

Starred and bookmarked 2026-05-29.

## Converging research directions

This proposal intersects with but differs from:
- **Task arithmetic** — we manipulate the native sparse substrate, not external adapters
- **LoRA composition** — similar goal, different mechanism
- **Feature steering** — we use weight deltas, not activation injection
- **Model editing** — we target clusters, not individual facts
- **Sparse autoencoder feature localization** — complementary interpretability approach
- **Neuroscience lesion studies** — the lesion testing phase is a direct analog

The key difference throughout: we are not adding external structure. We are working with
what the Hebbian training already produces.

## Future extensions

### Dormant vs active clusters

Not all clusters that exist structurally will fire under normal inference. Some circuits
may activate only under specific conditions — certain chain depths, retrieval loops,
self-referential prompts, or multi-stage reasoning sequences. Two cluster states:

**Active clusters** — fire reliably under standard probing conditions.

**Dormant clusters** — structurally present (weights exist, co-firing topology is there)
but silent under standard probes. May surface as:
- Latent competence — capability that exists but isn't reached by shallow probing
- Suppressed specialists — a circuit that loses activation competition to a dominant one
- Context-gated subnetworks — only fires when primed by a preceding inference chain

Detecting dormant clusters requires a second probe pass with deeper inference chains,
context priming, and possibly activation injection to force pathways open. Especially
relevant if Ninereeds later develops retrieval loops or self-reflection behavior.

### Developmental timelines

The atlas captures *what* exists at a point in time. A timeline captures *when* things
emerged and *why*:

- What clusters were present after run_N?
- What precursor structures existed before a capability appeared?
- What later capabilities depended on an earlier cluster?

This turns the atlas into a cognitive growth history — the ontogeny of Ninereeds'
competence. Concretely: run the full probe pass after every major training milestone,
store each map as a versioned artifact, then build a dependency graph:

```
spatial_ある [emerged run_13] → depends on: location_vocab [run_7], existential_predicate [run_9]
dative_transfer [emerged run_14] → depends on: receiver_role [run_11], verb_valency [run_9]
```

This also tells you what *not* to overwrite. If capability X depends on cluster Y,
ablating Y to fix an unrelated regression breaks X. The timeline makes those dependencies
explicit before they become surprises.

## Open questions

- Do Hebbian weight updates preserve cluster locality across runs, or do clusters drift?
  (Primary empirical question — the whole plan depends on the answer.)
- Can routing clusters be reliably separated from semantic clusters at useful precision?
- What is the right α for delta application? Fixed or tuned per specialist?
- Are cluster motifs stable across scales (150M → 604M → 1.2B)?
- Can the probe pass run fast enough to use after every epoch as a live diagnostic?
- Does lesion testing require surgery on weights, or can activation masking suffice?

## Related docs

- `docs/training.md` — training procedure and run history
- `docs/grammar_plan.md` — grammar curriculum (primary target for first specialist run)
- `docs/bdh_cognitive_os_design.md` — long-term architecture vision
- `todo.md` Phase D — run_13 is the first candidate for a post-run brain map
