# Brain Trace Report — c16_e5_redesign_current

- checkpoint: `core/c16_redesign_e5.pt`
- probes: 613
- concepts: 172
- positions: `prompt`
- edge threshold: 0.75

## Next-Move Signals

### Weak concepts: add cleaner/more varied corpus
- `stretch_noun` (body) fire=0.01511 active_dims=40914
  source: `training_data/redesign/words/body/stretch_noun_what_is.md`
- `moo` (sounds) fire=0.01528 active_dims=58660
  source: `training_data/redesign/words/sounds/moo_example.md`
- `crew` (people) fire=0.01537 active_dims=61115
  source: `training_data/redesign/words/people/crew_boundary_internal.md`
- `creator` (people) fire=0.01552 active_dims=61796
  source: `training_data/redesign/words/people/creator_boundary_internal.md`
- `format_verb` (shapes) fire=0.01561 active_dims=56028
  source: `training_data/redesign/words/shapes/format_verb_meaning.md`
- `habitat` (places) fire=0.01562 active_dims=63282
  source: `training_data/redesign/words/places/habitat_boundary_name.md`
- `twinkle_boundary` (sounds) fire=0.01565 active_dims=59202
  source: `training_data/redesign/words/sounds/twinkle_boundary_location.md`
- `crack of thunder` (sounds) fire=0.01566 active_dims=64896
  source: `training_data/redesign/words/sounds/crack of thunder_boundary_internal.md`
- `internet` (technology) fire=0.01568 active_dims=65825
  source: `training_data/redesign/words/technology/internet_appearance.md`
- `bold` (properties) fire=0.01570 active_dims=67332
  source: `training_data/redesign/words/properties/bold_boundary_why.md`

### Fuzzy categories: split or strengthen anchors
- `identity` concept_cos=0.606 concept_jaccard=0.440

### Cross-category connections: audit co-occurrence/noise
- `knee` ↔ `kennel` cosine=0.950 jaccard=0.876
- `stream` ↔ `stripe` cosine=0.942 jaccard=0.836
- `tile` ↔ `tank` cosine=0.939 jaccard=0.860
- `stone` ↔ `stripe` cosine=0.933 jaccard=0.867
- `queue` ↔ `quiver` cosine=0.926 jaccard=0.793
- `slide` ↔ `stripe` cosine=0.925 jaccard=0.865
- `moat` ↔ `den` cosine=0.925 jaccard=0.867
- `bone` ↔ `ball` cosine=0.924 jaccard=0.832
- `pulse` ↔ `plate` cosine=0.924 jaccard=0.885
- `knee` ↔ `den` cosine=0.923 jaccard=0.863

### Overconnected concepts: possible hubs/default patterns
- `term` degree=161
- `fade` degree=159
- `point` degree=159
- `name` degree=158
- `level` degree=158
- `hue` degree=156
- `update` degree=156
- `segment` degree=156
- `sick` degree=156
- `flight` degree=155

## Category Stats

| category | probes | concepts | fire_rate | concept_cos | concept_jaccard |
|---|---:|---:|---:|---:|---:|
| actions | 20 | 6 | 0.01638 | 0.788 | 0.725 |
| animals | 24 | 6 | 0.01690 | 0.835 | 0.769 |
| body | 19 | 6 | 0.01636 | 0.789 | 0.653 |
| clothing | 23 | 6 | 0.01665 | 0.851 | 0.771 |
| cognition | 23 | 6 | 0.01673 | 0.787 | 0.770 |
| colors | 21 | 6 | 0.01629 | 0.811 | 0.701 |
| communication | 24 | 6 | 0.01658 | 0.779 | 0.741 |
| emotions | 21 | 6 | 0.01637 | 0.811 | 0.745 |
| events | 20 | 6 | 0.01686 | 0.743 | 0.675 |
| food | 24 | 6 | 0.01645 | 0.832 | 0.744 |
| household | 21 | 6 | 0.01638 | 0.809 | 0.729 |
| identity | 12 | 4 | 0.01662 | 0.606 | 0.440 |
| language | 23 | 6 | 0.01640 | 0.792 | 0.761 |
| materials | 24 | 6 | 0.01636 | 0.841 | 0.744 |
| movement | 19 | 6 | 0.01670 | 0.757 | 0.691 |
| nature | 21 | 6 | 0.01634 | 0.840 | 0.743 |
| people | 20 | 6 | 0.01651 | 0.769 | 0.678 |
| places | 21 | 6 | 0.01638 | 0.825 | 0.713 |
| processes | 22 | 6 | 0.01620 | 0.752 | 0.720 |
| properties | 23 | 6 | 0.01625 | 0.819 | 0.745 |
| quantities | 21 | 6 | 0.01609 | 0.781 | 0.709 |
| shapes | 21 | 6 | 0.01643 | 0.798 | 0.715 |
| social | 22 | 6 | 0.01670 | 0.789 | 0.767 |
| sounds | 18 | 6 | 0.01605 | 0.705 | 0.663 |
| space | 20 | 6 | 0.01642 | 0.811 | 0.743 |
| states | 23 | 6 | 0.01650 | 0.770 | 0.749 |
| technology | 23 | 6 | 0.01635 | 0.753 | 0.669 |
| time | 16 | 6 | 0.01643 | 0.749 | 0.656 |
| tools | 24 | 6 | 0.01635 | 0.860 | 0.762 |

## Output Status

- `not_generated`: 613

## Interpretation

- Weak concepts are candidates for more direct anchor examples and template diversity.
- Fuzzy categories need either more examples or finer categories; do not assume one cluster exists.
- Cross-category edges are not automatically bad, but they are the first corpus co-occurrence audits to run.
- Overconnected concepts may be useful hubs or accidental defaults; verify with negative controls and output scoring.
