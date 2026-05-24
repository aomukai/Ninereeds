# Session Handoff

Date: 2026-05-24

Purpose: hand off current Ninereeds curriculum-expansion work to the next agent.

---

## Current Objective

Build a deterministic, function-first grammar curriculum for Ninereeds.

The immediate target is the German grammar/spatial curriculum, using German case
behavior as the spine and Japanese particles as cross-reference cues.

Primary docs:

- `todo.md`
- `docs/grammar_plan.md`
- `training_data/grammar/manifest.md`
- `training_data/grammar/lexicon.md`
- `training_data/grammar/prepositions.md`

---

## Last Clean Commit

Latest pushed checkpoint before current uncommitted work:

```text
70fa54ef Add ordered grammar curriculum scaffold
```

That commit added:

- `--no-shuffle` support in `train.py`
- grammar traversal in `meta/scripts/build_training_corpus.py`
- `meta/scripts/gen_grammar.py`
- `training_data/grammar/manifest.md`
- first `00_relation` grammar files
- docs/todo updates

---

## Current Checkpoint Work

Expected files/directories in the next checkpoint:

```text
M meta/scripts/build_training_corpus.py
M meta/scripts/gen_grammar.py
?? training_data/grammar/01_means_dative_anchor/
?? training_data/grammar/lexicon.md
?? training_data/grammar/prepositions.md
```

What changed in this checkpoint:

- Added `training_data/grammar/lexicon.md`
  - curated grammar-specific vocabulary
  - includes German gender, accusative, and dative forms
  - includes JP/ZH labels and role tags
- Added `training_data/grammar/prepositions.md`
  - local inventory of German prepositions
  - uses an external preposition page only as completeness reference
  - tiered into core two-way, dative anchors, accusative, genitive/formal, etc.
- Updated `meta/scripts/build_training_corpus.py`
  - skips grammar control files: `manifest.md`, `lexicon.md`, `prepositions.md`
- Updated `meta/scripts/gen_grammar.py`
  - added `01_means_dative_anchor` generation support
  - added `--limit` and `--offset`
  - increased DeepSeek output/time settings earlier:
    - `MAX_TOKENS = 32768`
    - `REQUEST_TIMEOUT = 300.0`
  - tightened validation for `mit` audit files
- Generated first 40 `mit` files in:
  - `training_data/grammar/01_means_dative_anchor/`
- Tightened `mit` generation after the first continuation batch exposed object
  drift in instrument files.

---

## Generated Grammar Files

Already committed:

```text
training_data/grammar/00_relation/001_relation_receiver.md
training_data/grammar/00_relation/002_place_source_target.md
training_data/grammar/00_relation/003_path_object_action.md
training_data/grammar/00_relation/004_owner_change_means.md
```

Generated in this checkpoint:

```text
training_data/grammar/01_means_dative_anchor/001_mit_accompaniment_dog.md
training_data/grammar/01_means_dative_anchor/002_mit_accompaniment_cat.md
training_data/grammar/01_means_dative_anchor/003_mit_accompaniment_child.md
training_data/grammar/01_means_dative_anchor/004_mit_accompaniment_woman.md
training_data/grammar/01_means_dative_anchor/005_mit_instrument_hammer.md
training_data/grammar/01_means_dative_anchor/006_mit_instrument_broom.md
training_data/grammar/01_means_dative_anchor/007_mit_instrument_pencil.md
training_data/grammar/01_means_dative_anchor/008_mit_vehicle_bus.md
training_data/grammar/01_means_dative_anchor/009_mit_vehicle_car.md
training_data/grammar/01_means_dative_anchor/010_mit_vehicle_train.md
training_data/grammar/01_means_dative_anchor/011_mit_accompaniment_dog.md
...
training_data/grammar/01_means_dative_anchor/025_mit_vehicle_boat.md
```

---

## Validation Status

Latest corpus dry-run passed after generating files `001` through `040`:

```text
Files:    24,981 / 24,981 included
Skipped:  0
All files validated — corpus is clean.
```

Latest targeted `mit` checks passed:

- all 40 generated `mit` files have 4 `[user]` / `[Ninereeds]` pairs
- no `mit das`
- no `mit die`
- no `mit den`
- vehicle English uses `by bus/car/train`, not `with the bus/car/train`
- instrument/vehicle files use people as agents, not animals
- no off-pool vehicle destinations after manual cleanup

Important audit finding:

- The first loose DeepSeek pass had good German case but semantic drift:
  - animals used as tool/vehicle agents
  - vehicle English said `with the bus`
  - some name translation
  - off-pool destinations such as `store` / `work`
- Tight prompt constraints fixed this for the 10-file `mit` audit batch.

Additional audit finding from files `011` through `025`:

- The first continuation pass invented off-lexicon instrument targets such as
  nail, fence, hallway, note, paper, shelf, and pipe.
- `meta/scripts/gen_grammar.py` now constrains instrument target nouns more
  tightly and rejects known off-lexicon drift.
- One regeneration produced Simplified Chinese (`锤`, `长`); the generator now
  rejects a small set of Simplified characters observed in this batch.
- The second continuation batch produced demonstratives (`その`, `那個`) and
  wagon/horse-carriage drift; the generator now rejects those patterns.

Conclusion:

- DeepSeek can handle `mit`, but only with tight preposition-specific prompts.
- The 10-file audit-before-scaling protocol is necessary.

---

## Next Action

Continue `mit` generation.

Plan agreed with user:

1. Keep the current 40-file `mit` set.
2. Generate the next continuation batch: `041` through `055`
   (`--offset 40 --limit 15`).
3. After each 15-file batch:
   - run automated checks
   - spot-audit 1-2 files manually
   - stop if drift appears
4. Commit after the full `mit` set is clean, or earlier if the next agent wants
   a safer checkpoint.

Suggested automated checks after each batch:

```bash
python3 -m py_compile meta/scripts/gen_grammar.py meta/scripts/build_training_corpus.py
python3 meta/scripts/build_training_corpus.py --dry-run
rg -n "mit das|mit die|mit den|with the (bus|car|train)|She|He|They|We| she | he | they | we |Sie| Er | sie | er |彼女|彼|她|他|我們|我们" training_data/grammar/01_means_dative_anchor
```

Also run a small script to count pairs and detect known drift, similar to:

```bash
python3 - <<'PY'
from pathlib import Path
import re
root=Path('training_data/grammar/01_means_dative_anchor')
for p in sorted(root.glob('*.md')):
    t=p.read_text(encoding='utf-8')
    bad=[]
    if len(re.findall(r'^\[user\]', t, re.M)) != 4:
        bad.append('bad_user_count')
    if len(re.findall(r'^\[Ninereeds\]', t, re.M)) != 4:
        bad.append('bad_ninereeds_count')
    if re.search(r'mit das|mit die|mit den', t):
        bad.append('bad_case')
    if re.search(r'with the (bus|car|train)', t, re.I):
        bad.append('bad_vehicle_en')
    print(p.name, 'ok' if not bad else ','.join(bad))
PY
```

---

## Generation Notes

DeepSeek model:

```text
deepseek/deepseek-v4-flash
```

It behaves like a thinking model:

- use `max_tokens=32768`
- allow long latency
- do not kill requests just because they take 1-3 minutes

OpenRouter key:

- available in repo root `.env`
- `.env` is gitignored
- `meta/scripts/gen_grammar.py` loads `.env`

Do not generate all prepositions at once.

For each new preposition:

1. Generate 10 test files.
2. Audit them.
3. If clean, continue with 6 batches of 15.
4. Stop early if drift appears.

The user explicitly wants this because DeepSeek may handle one preposition well
and another poorly.

---

## Training Constraint

Ordered curriculum runs must use:

```bash
--no-shuffle
```

Seeded shuffling is reproducible but destroys intended curriculum order.

No-shuffle smoke test already passed:

```text
sequential batch starts: [0, 4, 8, 12]
```

Do not launch run_13 until the grammar corpus is generated/audited and the run
corpus is built cleanly.

---

## Git Guidance

User pushed the previous snapshot before this work.

The last commit made by Codex was pushed:

```text
70fa54ef Add ordered grammar curriculum scaffold
```

If continuing for a while, commit/push after each clean preposition batch or
after a safe tooling milestone.
