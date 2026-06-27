# Brain Trace Manual

## Purpose

The brain trace scanner turns activation maps into training decisions.

The older `probe -> hubs -> graph` workflow shows probe similarity. That remains useful
for visual inspection. The newer `trace` workflow adds concept metadata, firing
frequency, co-firing overlap, generated-output status, and a Markdown report that points
to likely corpus actions.

Use it when you need to answer:

- Which concepts are weak?
- Which concepts fire together?
- Which categories are fuzzy?
- Which concepts act like broad default hubs?
- Which corpus area should be strengthened or audited next?

## Required Probe Schema

Every non-comment JSONL record in `training/corpus_admin/probe_sets/*.jsonl` should
include these fields:

```json
{
  "id": "ani_01",
  "campaign": "c16",
  "category": "animals",
  "lang": "EN",
  "language": "EN",
  "concept_id": "dog",
  "template_id": "what_is",
  "probe_role": "definition",
  "construction_id": "what_is",
  "source_corpus": "training/corpus_admin/probe_sets/c16_concepts.jsonl",
  "prompt": "[user]what is a dog?\n[Ninereeds]",
  "expected_cluster": "animals",
  "expected_behavior": "answer about dog; expected activation cluster: animals"
}
```

Field meanings:

| Field | Meaning |
|---|---|
| `id` | Unique probe ID. |
| `campaign` | Probe family or training campaign. |
| `category` | Broad diagnostic group, such as `animals`, `arithmetic`, or `grammar`. |
| `lang` | Legacy language field kept for compatibility. |
| `language` | Canonical language field used by trace reports. |
| `concept_id` | Stable concept being tested. Same concept across languages/templates must use the same ID. |
| `template_id` | Question frame, such as `what_is`, `look_like`, `boolean`, or `arithmetic_exact`. |
| `probe_role` | Diagnostic purpose, such as `definition`, `property_boolean`, `cross_language_alignment`, or `unknown_boundary`. |
| `construction_id` | Specific construction, operation, or frame. For grammar, use specific cases/constructions. |
| `source_corpus` | Source file or corpus path for provenance. |
| `prompt` | Exact prompt sent to the model. |
| `expected_cluster` | Intended activation family. This is not proof of correctness. |
| `expected_behavior` | Human-readable behavior expectation for report review. |

## Validation

Validate all probe sets before a trace run:

```bash
python3 meta/scripts/brain_map.py validate-probes training/corpus_admin/probe_sets
```

Validate one file:

```bash
python3 meta/scripts/brain_map.py validate-probes training/corpus_admin/probe_sets/c16_concepts.jsonl
```

Strict validation checks:

- required fields exist and are non-empty
- probe IDs are unique
- `lang` and `language` agree
- `concept_id` is not just the probe ID

## Current Redesign Probe Set

The current redesign corpus is EN-first and lives under:

```text
training_data/redesign/identity/
training_data/redesign/words/<bucket>/
```

The maintained current-corpus probe set is:

```text
training/corpus_admin/probe_sets/redesign_current.jsonl
```

It is generated from the actual redesign corpus, not hand-written. Regenerate it after
large corpus changes:

```bash
python3 meta/scripts/build_redesign_probe_set.py \
  --output training/corpus_admin/probe_sets/redesign_current.jsonl \
  --concepts-per-bucket 6 \
  --angles-per-concept 4 \
  --identity-limit 12 \
  --seed 1337
```

Default behavior:

- samples every current word bucket
- includes identity probes
- uses clean known angle families only
- excludes `_rephrase` files unless requested
- excludes unusual filename angles unless requested

Useful generator options:

| Option | Use |
|---|---|
| `--concepts-per-bucket N` | Wider or smaller concept coverage per bucket. |
| `--angles-per-concept N` | More or fewer probe angles per concept. |
| `--include-rephrases` | Include `_rephrase` files to test paraphrase routes. |
| `--allow-other-angles` | Include unusual angle names for audit/debug passes. |
| `--seed N` | Stable deterministic sampling. |

Use the old `c16_concepts.jsonl` as a small smoke set only. It does not represent the
current full redesign corpus.

## Standard Trace Run

Run the scanner with prompt-token tracing:

```bash
/home/aomukai/.unsloth/studio/unsloth_studio/bin/python meta/scripts/brain_map.py trace \
  --checkpoint checkpoints/c16_concept_anchoring_winner.pt \
  --probes training/corpus_admin/probe_sets/redesign_current.jsonl \
  --name redesign_current_trace \
  --positions prompt \
  --top-k 32
```

Outputs:

| Output | Purpose |
|---|---|
| `tmp/brain_trace_<name>.npz` | Compact numeric arrays for deeper analysis. |
| `training/logs/brain_maps/<name>_trace.json` | Machine-readable summary. |
| `training/logs/brain_maps/<name>_trace_report.md` | Human-readable next-move report. |

Use `--positions prompt` for normal diagnostics. It measures firing over all prompt
tokens and is better for "how often does this fire?"

Use `--positions last` only for compatibility with the old final-token scan.

## Trace With Output Behavior

To include generated answers and cheap output-status labels:

```bash
/home/aomukai/.unsloth/studio/unsloth_studio/bin/python meta/scripts/brain_map.py trace \
  --checkpoint checkpoints/c16_concept_anchoring_winner.pt \
  --probes training/corpus_admin/probe_sets/redesign_current.jsonl \
  --name redesign_current_trace_gen \
  --positions prompt \
  --generate
```

Output statuses are heuristic:

| Status | Meaning |
|---|---|
| `generated` | Non-empty output with no obvious loop/garble signal. |
| `unknown` | Output appears to use an "I don't know" style response. |
| `loop` | Output appears repetitive. |
| `garbled` | Output has likely decoding/control-character damage. |
| `empty` | No generated content. |
| `not_generated` | `--generate` was not used. |

These labels are not correctness grades. Real correctness requires future probe fields
with expected answers or scorer rules.

## Report Interpretation

The report starts with "Next-Move Signals." Treat these as triage, not verdicts.

### Weak Concepts

Weak concepts have low average firing rate relative to the probe set.

Likely actions:

- add direct anchor examples
- add multiple templates for the same concept
- add grounded examples using varied contexts
- check whether the concept appears too rarely in the corpus

Do not blindly oversample. First check whether the concept is intentionally rare or
whether the probe wording is poor.

### Fuzzy Categories

Fuzzy categories have low intra-category concept similarity.

Likely actions:

- split the category into finer constructions
- add category-level contrast examples
- add more examples per concept
- check whether the category is too broad

Example: "dative" should not be one category if static location, companion, and
recipient constructions activate differently.

### Cross-Category Connections

Cross-category edges show concepts from different categories with high cosine or
Jaccard overlap.

Likely actions:

- inspect corpus co-occurrence
- look for repeated story frames that bind unrelated concepts
- add contrastive examples if the connection is wrong
- leave it alone if the connection is naturally correct

These are not automatically failures. `dog` and `bark` should connect. `sugar` and
`sadness` probably should not.

### Overconnected Concepts

Overconnected concepts have many strong edges.

Possible interpretations:

- useful hub concept
- repeated corpus default
- prompt-template artifact
- broad language/control circuit

Likely actions:

- add negative controls
- compare `last` vs `prompt` traces
- run with multiple templates
- check whether one corpus frame repeats too often

## Numeric Metrics

| Metric | Meaning |
|---|---|
| `avg_fire_rate` | Mean fraction of traced token positions where dimensions fire for a concept. |
| `active_dims` | Number of dimensions that fired at least once for that concept. |
| `cosine` | Similarity of mean activation vectors. Good for geometry. |
| `jaccard` | Overlap of active dimensions. Good for "what fires with what." |
| `degree` | Number of strong concept connections above threshold. |

Cosine and Jaccard answer different questions. High cosine with low Jaccard means similar
direction but different active support. High Jaccard means actual co-firing overlap.

## Recommended Epoch Workflow

After each meaningful checkpoint:

```bash
python3 meta/scripts/brain_map.py validate-probes training/corpus_admin/probe_sets

/home/aomukai/.unsloth/studio/unsloth_studio/bin/python meta/scripts/brain_map.py trace \
  --checkpoint "$CKPT" \
  --probes training/corpus_admin/probe_sets/redesign_current.jsonl \
  --name "$NAME" \
  --positions prompt \
  --top-k 32
```

Then read:

```bash
less training/logs/brain_maps/${NAME}_trace_report.md
```

Decision loop:

1. Check weak concepts.
2. Check fuzzy categories.
3. Check suspicious cross-category links.
4. Audit the relevant corpus files.
5. Add or repair targeted examples.
6. Retrain or continue training.
7. Run the same trace again and compare reports.

## Probe Design Rules

Use these rules for new probes:

- Same concept across templates must share `concept_id`.
- Same concept across languages must share `concept_id`.
- Different question frames must use different `template_id`.
- Grammar categories must use specific `construction_id`, not broad case labels only.
- Boundary probes should keep the underlying concept in `concept_id` and use `probe_role: "unknown_boundary"` or another boundary role.
- Use `expected_behavior` to describe what a human should check.

Good:

```json
{"concept_id":"dog","template_id":"what_is","probe_role":"definition"}
{"concept_id":"dog","template_id":"property_boolean","probe_role":"property_boolean"}
{"concept_id":"dog","template_id":"cross_language_what_is","language":"DE"}
```

Bad:

```json
{"concept_id":"an_prop_01"}
{"concept_id":"dog_DE"}
{"concept_id":"dative"}
```

## Current Limits

The trace scanner still does not prove semantic ownership.

It measures activation geometry, firing frequency, and co-firing overlap. A concept is
more credible when it is stable across templates, languages, output behavior, and
checkpoint comparisons. Causal claims still require lesion or masking tests.

Use trace reports to choose the next corpus or training intervention, not to declare that
a concept has been fully understood.
