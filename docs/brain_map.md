# Brain Map — Activation Atlas and Modular Training

## Core idea

Ninereeds' 3–5% activation sparsity (inherited from the BDH-GPU architecture) means that
different concepts activate largely non-overlapping neuron subsets. This makes it possible
to *map* the model's internal state and to *transplant* specific capabilities between
checkpoints without carrying unrelated regressions.

The model is treated less like a monolithic function approximator and more like a living
circuit atlas — closer to modular cortical recruitment than transformer-style feature
superposition.

## Why sparsity enables this

In a dense transformer, features are superposed across neurons. Disentangling a specific
capability from a checkpoint requires careful probing and is still largely unsolved.
In a sparse Hebbian network, a concept that has been learned tends to live in a tight,
identifiable cluster. If you can label the cluster, you can target it.

This property must be empirically verified — it is plausible but not guaranteed to hold
beyond toy examples. The first brain map pass is also a test of the premise itself.

## Cluster taxonomy

Not all clusters are equal. Two types must be distinguished during analysis:

**Semantic clusters** — encode a learned concept directly. Examples: "dative recipient
transfer", "spatial containment", "animal category", "Japanese existential ある".
These are the transplantation targets.

**Routing clusters** — coordinate activation flow between regions. They appear across many
unrelated probes and have high co-firing centrality. They are not concept-specific and
should be identified and filtered before labeling. Treating a routing hub as a semantic
cluster would produce a meaningless transplant.

Practical separation: rank neurons by how many distinct probe categories they activate
across. High-rank neurons are routing candidates; low-rank, high-coherence subsets are
semantic candidates.

## Cluster identity and stability

Neuron IDs alone are a fragile representation of a cluster. Even in sparse systems,
clusters can drift, split, or reassign neurons between training runs. Define clusters
by multiple signatures:

- **Centroid** — mean activation vector over the cluster's probe set
- **Co-firing statistics** — which neurons tend to activate together
- **Topology** — graph structure of connections within the cluster
- **Probe coverage** — which input prompts reliably activate the cluster

This way "the dative cluster" can be recognized even if 20% of its constituent neurons
rotate out between runs. Local motifs probably survive scale changes; exact coordinates
probably do not.

## Plan

### Phase 1 — Brain map (post solid-foundation run)

1. Write a comprehensive probe script (`meta/scripts/brain_map.py` or extend `probe.py`).
   - One inference per trained concept (every phase file question, every grammar probe,
     every language form taught in lang_1–5).
   - Record activation pattern per inference: which neurons, which layers, magnitude.
2. Identify routing clusters (high cross-category centrality) and separate them.
3. Cluster the remaining activation vectors (k-means or UMAP + DBSCAN).
4. Label each cluster by inspecting which probes activate it.
5. Represent the atlas as a graph, not flat labels:
   ```
   dative_cluster:
     connected_to: [transfer_verbs, spatial_relations, pronoun_resolution]
   ```
6. Write the map to a JSON artifact: `{cluster_id: {label, neurons, centroid, topology, probe_examples}}`.
7. Visualize — see reference below.

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
