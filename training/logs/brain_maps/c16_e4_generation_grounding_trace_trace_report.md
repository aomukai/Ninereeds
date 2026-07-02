# Brain Trace Report — c16_e4_generation_grounding_trace

- checkpoint: `chat/ninereeds.pt`
- probes: 7
- concepts: 3
- positions: `prompt`
- edge threshold: 0.75

## Next-Move Signals

### Weak concepts: add cleaner/more varied corpus
- `dog` (animals) fire=0.01490 active_dims=109363
  source: `training_data/redesign/words/animals/dog_appearance.md`

### Cross-category connections: audit co-occurrence/noise
- `airport` ↔ `airplane` cosine=0.776 jaccard=0.756
- `dog` ↔ `airplane` cosine=0.747 jaccard=0.795

### Overconnected concepts: possible hubs/default patterns
- `airplane` degree=2
- `dog` degree=1
- `airport` degree=1

## Category Stats

| category | probes | concepts | fire_rate | concept_cos | concept_jaccard |
|---|---:|---:|---:|---:|---:|
| animals | 4 | 1 | 0.01490 |  |  |
| places | 1 | 1 | 0.01565 |  |  |
| tools | 2 | 1 | 0.01621 |  |  |

## Output Status

- `generated`: 6
- `unknown`: 1

## Interpretation

- Weak concepts are candidates for more direct anchor examples and template diversity.
- Fuzzy categories need either more examples or finer categories; do not assume one cluster exists.
- Cross-category edges are not automatically bad, but they are the first corpus co-occurrence audits to run.
- Overconnected concepts may be useful hubs or accidental defaults; verify with negative controls and output scoring.
