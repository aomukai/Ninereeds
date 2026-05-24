# Session Handoff

Date: 2026-05-25

Purpose: hand off current Ninereeds grammar-curriculum work to the next agent
from a clean repo boundary.

---

## Current Objective

Build a deterministic, function-first grammar curriculum for Ninereeds.

The grammar work is organized around German case behavior, with Japanese
particles used as cross-reference cues. Corpus order matters and training runs
for this curriculum must stay deterministic.

Primary docs:

- `todo.md`
- `docs/grammar_plan.md`
- `training_data/grammar/manifest.md`
- `training_data/grammar/lexicon.md`
- `training_data/grammar/prepositions.md`

---

## Current State

Repo state at handoff:

- working tree clean
- `main` synced with `origin/main`
- latest pushed commit:

```text
610fd5de Complete aus grammar batch
```

Grammar progress:

1. `00_relation` is complete.
2. `01_means_dative_anchor/mit` is complete at `001` through `100`.
3. `01_means_dative_anchor/bei` is complete at `101` through `200`.
4. `01_means_dative_anchor/aus` is complete at `201` through `300`.
5. Next work should begin at the next preposition from a clean boundary.

Latest corpus validation:

```text
Files:    25,241 / 25,241 included
Fixed:    1,088
Skipped:  0
All files validated — corpus is clean.
```

---

## What Was Finished

Completed in the current grammar phase:

- deterministic grammar traversal is wired into
  `meta/scripts/build_training_corpus.py`
- grammar generation is handled by `meta/scripts/gen_grammar.py`
- grammar control docs are in place:
  - `training_data/grammar/manifest.md`
  - `training_data/grammar/lexicon.md`
  - `training_data/grammar/prepositions.md`
- full audited sets were generated for:
  - `mit`
  - `bei`
  - `aus`

Important generator behavior now encoded in `meta/scripts/gen_grammar.py`:

- supports `--limit`, `--offset`, `--dry-run`, and `--force`
- uses DeepSeek with long output and timeout settings
- validates grammar files structurally and semantically
- contains preposition-specific drift guards, especially for:
  - `mit` instrument/vehicle drift
  - `bei` static-nearby drift
  - `aus` source-only and window-source drift

---

## Known Working Protocol

This protocol worked and should be reused for the next preposition:

1. Generate 10 audit files first.
2. Spot-audit them manually.
3. If clean, continue with 6 batches of 15.
4. After each 15-file batch:
   - run corpus dry-run validation
   - spot-audit 1-2 risky files
   - tighten validator rules immediately if drift appears
5. Commit and push at clean checkpoints.

The user explicitly wants this because DeepSeek may handle one preposition well
and another poorly.

---

## Next Action

Start the next dative-anchor preposition from a clean boundary.

Likely candidates already discussed:

- `von`
- `zu`

Recommended first step:

1. choose the next preposition
2. add or extend the dedicated audit cluster in `meta/scripts/gen_grammar.py`
3. generate the first 10 audit files
4. validate and spot-audit before scaling

---

## Validation Commands

Run these after each generation batch:

```bash
python3 -m py_compile train.py meta/scripts/build_training_corpus.py meta/scripts/gen_grammar.py
python3 meta/scripts/build_training_corpus.py --dry-run
```

For targeted inspection, read the new files directly and use `rg` for known
drift patterns in `training_data/grammar/01_means_dative_anchor/`.

---

## Training Constraint

Ordered curriculum runs must use:

```bash
--no-shuffle
```

The user wants deterministic sample order for direct comparisons across runs.

---

## Model / Runtime Notes

DeepSeek model used for grammar generation:

```text
deepseek/deepseek-v4-flash
```

Operational notes:

- use long timeouts
- do not kill requests just because they are quiet for several minutes
- long silent stretches are normal
- low-frequency polling is better than aggressive polling

OpenRouter key:

- available in repo root `.env`
- `.env` is gitignored
- `meta/scripts/gen_grammar.py` loads it
