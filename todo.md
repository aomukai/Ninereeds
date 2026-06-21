# TODO

Active tasks only. When a task is done: delete it here, add an entry to `history.md`.

---

## Corpus redesign — active

- Retry 53 failed words from angle_gen run (in progress — `--retry-failed`)
- Run `angle_aug.py --wave 1` (clean rephrasing pass) after Tier 1 training verified working
- Run `angle_aug.py --wave 2` (yes/no + negation) after Wave 1 verified
- Run `angle_aug.py --wave 3` (natural chat phrasings) after Wave 2 verified
- Build corpus .txt from `training_data/redesign/` for first training run
- Update `build_training_corpus.py` to scan redesign layout (identity/ + words/ buckets)
- Design new eval probe sets: concept accuracy, boundary accuracy, identity accuracy

---

## Training — next

- First epoch: redesign corpus on 25M model
- Brain scan after epoch 1
- Run `eval_concept.py` after epoch 1
- Chat session with result — human impression eval
- Compare 25M vs 150M on same corpus (same eval, side by side)

---

## Pipeline infrastructure

- Build `meta/scripts/campaign_runner.py` — spec in `training/pipeline/pipeline.md`

---

## Standing (no urgency)

- Fix 387 inverted K-8 education files in `training_data/04_education/dialogues/`
- JP-specific corpus from imabi.org / guidetojapanese.org — if JP gap confirmed structural
- Wiki splitting into single-concept files — needed for fine-grained ordering
