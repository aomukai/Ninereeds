# TODO

Active tasks only. When a task is done: delete it here, add an entry to `history.md`.

---

## Corpus redesign — campaign roadmap

Snowflake strategy: prove each layer before adding next. One campaign per step.

**C16 — COMPLETE. Winner: E4 (`checkpoints/c16_concept_anchoring_winner.pt`)**
- Concept anchoring, simple questions, EN-only.
- Peaked at E4 (shaped=0.996, flags=0, chat=9/12). E5 regressed → stopped.
- Key finding: still learning at E4 vs prior campaigns peaking E2/E3. Recipe confirmed.

**C16A — IN PROGRESS: paraphrase pass**
- Every source file in `training_data/redesign/words/` gets a `_rephrase` sibling.
- Same facts, varied question surface only.
- Runner: `angle_aug.py --wave 1` → `aug_done.txt` progress
- Log: `tmp/aug_rephrase_openrouter.log`
- Train from C16 E4 winner once aug pass completes. Eval same signals.
- Signal to watch: does on-topic chat rate improve beyond 9/12? Do weak-bucket after-hub scores recover?

**C16B — NEXT: paraphrase + targeted structural augmentation**
- Build new supplementary files (as `_supplement` siblings) targeting diagnosed weak buckets:
  - **Food:** add explicit "X is food. People eat X." spine files; fix non-living boundary→negation files
  - **Nature:** add `_category` angle ("A river is a natural thing.") to resolve water-overlap blur
  - **Actions:** expand corpus (only 90 files); add action-spine angle ("Running is an action."); fix capability angle agent-bleeding
  - **Emotions:** expand `_situation` angle to all emotions (grounding in observable scene)
  - **Boundary (non-living):** convert "does X dream?" → negation ("An almond does not dream. An almond is not an animal.") for food, nature, colors
- All new files are `_supplement` siblings alongside originals and `_rephrase` files.
- Train from best C16A checkpoint.

**C16C — LATER: longer sentences (1–2 conjunctions)**
- New generated files: "A dog is an animal that has fur and barks."
- One relative clause or conjunction per sentence — not deeper.
- Goal: start encoding relations between properties, not just flat property lists.
- Particularly useful for weak buckets: "An almond is food that people eat." / "A river is a natural thing that flows across land." / "Happiness is a feeling that a person has when things are good."
- Requires a new generator pass (not yet built). Build after C16B confirmed.

**C17 — LATER: yes/no + negation (`angle_aug.py --wave 2`)**

**C18 — LATER: natural chat phrasings (`angle_aug.py --wave 3`)**

**C19 — LATER: stories**

Each campaign waits for the previous to show a clear signal.

---

## C16A paraphrase pass — monitoring

- PID: 6576 (openrouter, 4 workers) — restarted clean 2026-06-22
- Progress: `wc -l training_data/redesign/aug_done.txt`
- Files done: 0/33966 at launch
- ETA: ~5–6 hours from launch
- After completion: update `training/corpus/redesign_c16a.txt` manifest → train 1 epoch from C16 E4

---

## Pipeline infrastructure

- Build `meta/scripts/campaign_runner.py` — spec in `training/pipeline/pipeline.md`

---

## Standing (no urgency)

- Fix 387 inverted K-8 education files in `training_data/04_education/dialogues/`
- Update `angle_gen.py` BUCKETS dict to match `rebucket.py` (24 buckets)
- JP-specific corpus from imabi.org / guidetojapanese.org — if JP gap confirmed structural
- Wiki splitting into single-concept files — needed for fine-grained ordering
