# TODO

Active work queue. See `docs/training.md` for the full procedure.

---

## Checkpoint lineage

| Run | Base | Best epoch | Shaped | Promoted checkpoint |
|---|---|---|---|---|
| run_1 | scratch | E5 (5-epoch baseline) | — | `checkpoints/run1_e5.pt` |
| run_2 | run1_e5 | E3 | 0.922 | `checkpoints/run2_e3.pt` (not yet promoted — still at `core/run_2_grounding_stories_from_run1_e5_e3.pt`) |
| run_3 | run1_e5 | E2 | 0.925 | `checkpoints/run3_e2.pt` |
| run_4 | run3_e2 | E4 | 0.943 | `checkpoints/run4_e4.pt` |
| run_5 | run4_e4 | E2 (reasoning probe peak) | 0.910 | `checkpoints/run5_e2.pt` |
| run_6 | run4_e4 | E3 | 0.916 | `checkpoints/run6_e3.pt` |
| run_7 | run4_e4 | E1 | 0.924 | `checkpoints/run7_e1.pt` |
| run_8 | run7_e1 | E2 | 0.906 | `checkpoints/run8_e2.pt` |
| run_9 | run7_e1 | — | — | discarded (MSM failed: 1 optimizer update, shaped 0.905) |
| run_10 | run7_e1 | E1 | 0.901 | `core/run_10_counting_e1.pt` (scaling study only — not promoted) |

## Current best by category

| Category | Checkpoint | Evidence |
|---|---|---|
| Best overall inference | `checkpoints/run4_e4.pt` | Shaped 0.943, 1 loop, positive shaper delta |
| Best reasoning probe | `checkpoints/run5_e2.pt` | First correct arithmetic ("two plus two is four"); "Zero is a number" structured |
| Best low-loop | `checkpoints/run3_e2.pt` | 0 loops, shaped 0.925 |
| Best multilingual | `checkpoints/run6_e3.pt` | German dative "über dem Berg" correct spontaneously at E3; JP spatial structure present |
| Best raw score | `checkpoints/run4_e4.pt` | Raw 0.919 |

---

## Scaling study — runs 10 / 11 / 12 — COMPLETE

Two-step ablation: depth fixed at n_layer=6, vary width and per_layer_weights. Same corpus (run10_corpus.txt), 1 epoch each.

| Run | Actual params | Config | What varies | Flag | Status |
|---|---|---|---|---|---|
| run_10 | 25.3M | n_layer=6 n_embd=256 shared weights | baseline | *(default)* | COMPLETE — E1 shaped 0.901, arith 0/3 |
| run_11 | 151.1M | n_layer=6 n_embd=256 per_layer_weights | shared→independent | `--scale-150m` | COMPLETE — E1 shaped 0.913, arith 0/3, FC 1/8 |
| run_12 | 604.2M | n_layer=6 n_embd=512 per_layer_weights | narrow→wide | `--scale-600m` | COMPLETE — E1 shaped 0.915, arith 0/3, FC 0/8 |

**Verdict:** Arithmetic 0/3 at all three scales. Echo pressure is a curriculum problem, not a capacity problem.
Width increase (151M→604M): improved RAW 0.873→0.913, reduced loops 2→1, shaped +0.002. Not a breakthrough.
**Decision:** Max out 150M with curriculum improvements. Grammar-function cluster ordering is the next intervention.
Reports: `training/logs/run_10_report.md`, `run_11_report.md`, `run_12_report.md`

---

## Next: run_13 — grammar-function cluster ordering (150M)

**Goal:** Test whether dependency-ordered grammar clusters fix echo pressure and dative/accusative confusion.

**Prerequisite steps (in order):**

- [ ] Design cluster sequence: map existing corpus files to grammar-function clusters
      (dative cluster → accusative cluster → math cluster → narrative → philosophy)
      Target file: `docs/cluster_sequence.md` or similar planning doc
- [ ] Update `meta/scripts/build_training_corpus.py` to emit files in cluster order (not random/alphabetical)
- [ ] Build `training/corpus/run13_corpus.txt` with new ordered sequence
- [ ] Launch run_13 at 150M: `python3 train.py --scale-150m --epochs 3`
- [ ] Run probe + eval after each epoch; fill `training/logs/run_13_report.md`

**Hardware note:** Second RTX 3060 install week of 2026-06-01. After install:
- Pin training to dedicated GPU: `CUDA_VISIBLE_DEVICES=1`
- 604M can run at batch_size=8 with standard AdamW (drop --adam8bit)
- 1.2B model (n_layer=12, n_embd=512) becomes testable on dedicated card

## Training runs (historical)

### Run 6 — `oversample_cluster` reasoning ×2 — COMPLETE
- Base: `checkpoints/run4_e4.pt` (shaped 0.943)
- Corpus: `training/corpus/run6_corpus.txt` (13.65 MB)
- Result: E3 best (shaped 0.916, loops 2). Success criteria NOT met — no arithmetic breakthrough, shaped below 0.943. Dose approach exhausted: ×4 bleed, ×2 insufficient.
- Notable: German dative "über dem Berg" appeared spontaneously at E3.
- Log: `training/logs/run_6_train.log` | Report: `training/logs/run_6_report.md`

### Run 8 — `grounded_story_arithmetic` state-change stories — COMPLETE
- Base: `checkpoints/run7_e1.pt` (shaped 0.924, format transfer confirmed)
- Corpus: `training/corpus/run8_corpus.txt` (13.49 MB, 24,901 files)
- Intervention: 18 arithmetic state-change stories ×4 languages added to grounded_stories; story 47 bridges "is"/"equals" explicitly; story 48 introduces Bello (1+1=2)
- Epochs: 5
- Log: `training/logs/run_8_train.log` | Report: `training/logs/run_8_report.md`

### Run 7 — `teacher_student_drill` arithmetic — COMPLETE
- Base: `checkpoints/run4_e4.pt` (shaped 0.943, best overall)
- Corpus: `training/corpus/run7_corpus.txt` (13.43 MB, 24,829 files)
- Intervention: 12 arithmetic drill files generated via DeepSeek in direct probe format (what is X plus X? → X plus X is Y.); reasoning section 108→120 files, no oversampling
- Justification: existing reasoning files use multi-modal "Teach me about..." format — format mismatch with probe. Drill files directly train the expected Q&A pattern.
- Log: `training/logs/run_7_train.log` | Report: `training/logs/run_7_report.md`
