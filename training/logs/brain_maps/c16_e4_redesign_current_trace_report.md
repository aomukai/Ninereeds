# Brain Trace Report — c16_e4_redesign_current

- checkpoint: `core/c16_redesign_e4.pt`
- probes: 613
- concepts: 172
- positions: `prompt`
- edge threshold: 0.75

## Next-Move Signals

### Weak concepts: add cleaner/more varied corpus
- `stretch_noun` (body) fire=0.01546 active_dims=41221
  source: `training_data/redesign/words/body/stretch_noun_what_is.md`
- `crack of thunder` (sounds) fire=0.01582 active_dims=64488
  source: `training_data/redesign/words/sounds/crack of thunder_boundary_internal.md`
- `format_verb` (shapes) fire=0.01585 active_dims=56427
  source: `training_data/redesign/words/shapes/format_verb_meaning.md`
- `habitat` (places) fire=0.01594 active_dims=62580
  source: `training_data/redesign/words/places/habitat_boundary_name.md`
- `crew` (people) fire=0.01602 active_dims=61856
  source: `training_data/redesign/words/people/crew_boundary_internal.md`
- `parent-offspring care system design` (processes) fire=0.01603 active_dims=82954
  source: `training_data/redesign/words/processes/parent-offspring care system design_example.md`
- `moo` (sounds) fire=0.01618 active_dims=59916
  source: `training_data/redesign/words/sounds/moo_example.md`
- `breath` (body) fire=0.01620 active_dims=61926
  source: `training_data/redesign/words/body/breath_appearance.md`
- `twinkle_boundary` (sounds) fire=0.01620 active_dims=60465
  source: `training_data/redesign/words/sounds/twinkle_boundary_location.md`
- `creator` (people) fire=0.01622 active_dims=62845
  source: `training_data/redesign/words/people/creator_boundary_internal.md`

### Fuzzy categories: split or strengthen anchors
- `identity` concept_cos=0.610 concept_jaccard=0.463

### Cross-category connections: audit co-occurrence/noise
- `stream` ↔ `stripe` cosine=0.946 jaccard=0.845
- `knee` ↔ `kennel` cosine=0.944 jaccard=0.879
- `tile` ↔ `tank` cosine=0.941 jaccard=0.866
- `stone` ↔ `stripe` cosine=0.936 jaccard=0.874
- `queue` ↔ `quiver` cosine=0.931 jaccard=0.807
- `slide` ↔ `stripe` cosine=0.928 jaccard=0.876
- `pulse` ↔ `plate` cosine=0.927 jaccard=0.895
- `den` ↔ `tank` cosine=0.926 jaccard=0.869
- `bone` ↔ `ball` cosine=0.926 jaccard=0.842
- `knee` ↔ `den` cosine=0.926 jaccard=0.875

### Overconnected concepts: possible hubs/default patterns
- `term` degree=163
- `name` degree=161
- `point` degree=161
- `fade` degree=160
- `half` degree=160
- `hue` degree=159
- `measure` degree=159
- `stdin` degree=159
- `flight` degree=158
- `level` degree=158

## Category Stats

| category | probes | concepts | fire_rate | concept_cos | concept_jaccard |
|---|---:|---:|---:|---:|---:|
| actions | 20 | 6 | 0.01701 | 0.790 | 0.734 |
| animals | 24 | 6 | 0.01752 | 0.838 | 0.786 |
| body | 19 | 6 | 0.01687 | 0.794 | 0.665 |
| clothing | 23 | 6 | 0.01719 | 0.849 | 0.782 |
| cognition | 23 | 6 | 0.01742 | 0.795 | 0.777 |
| colors | 21 | 6 | 0.01694 | 0.813 | 0.714 |
| communication | 24 | 6 | 0.01713 | 0.783 | 0.749 |
| emotions | 21 | 6 | 0.01706 | 0.812 | 0.756 |
| events | 20 | 6 | 0.01747 | 0.750 | 0.688 |
| food | 24 | 6 | 0.01708 | 0.837 | 0.757 |
| household | 21 | 6 | 0.01693 | 0.814 | 0.742 |
| identity | 12 | 4 | 0.01733 | 0.610 | 0.463 |
| language | 23 | 6 | 0.01701 | 0.799 | 0.771 |
| materials | 24 | 6 | 0.01701 | 0.843 | 0.756 |
| movement | 19 | 6 | 0.01734 | 0.763 | 0.702 |
| nature | 21 | 6 | 0.01698 | 0.841 | 0.755 |
| people | 20 | 6 | 0.01723 | 0.770 | 0.694 |
| places | 21 | 6 | 0.01702 | 0.824 | 0.724 |
| processes | 22 | 6 | 0.01679 | 0.759 | 0.731 |
| properties | 23 | 6 | 0.01693 | 0.818 | 0.757 |
| quantities | 21 | 6 | 0.01672 | 0.789 | 0.721 |
| shapes | 21 | 6 | 0.01699 | 0.805 | 0.727 |
| social | 22 | 6 | 0.01737 | 0.795 | 0.774 |
| sounds | 18 | 6 | 0.01670 | 0.712 | 0.677 |
| space | 20 | 6 | 0.01718 | 0.815 | 0.755 |
| states | 23 | 6 | 0.01719 | 0.774 | 0.759 |
| technology | 23 | 6 | 0.01692 | 0.758 | 0.681 |
| time | 16 | 6 | 0.01720 | 0.753 | 0.671 |
| tools | 24 | 6 | 0.01701 | 0.859 | 0.774 |

## Output Status

- `not_generated`: 613

## Interpretation

- Weak concepts are candidates for more direct anchor examples and template diversity.
- Fuzzy categories need either more examples or finer categories; do not assume one cluster exists.
- Cross-category edges are not automatically bad, but they are the first corpus co-occurrence audits to run.
- Overconnected concepts may be useful hubs or accidental defaults; verify with negative controls and output scoring.
