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

## Current best by category

| Category | Checkpoint | Evidence |
|---|---|---|
| Best overall inference | `checkpoints/run4_e4.pt` | Shaped 0.943, 1 loop, positive shaper delta |
| Best reasoning probe | `checkpoints/run5_e2.pt` | First correct arithmetic ("two plus two is four"); "Zero is a number" structured |
| Best low-loop | `checkpoints/run3_e2.pt` | 0 loops, shaped 0.925 |
| Best multilingual | `checkpoints/run6_e3.pt` | German dative "über dem Berg" correct spontaneously at E3; JP spatial structure present |
| Best raw score | `checkpoints/run4_e4.pt` | Raw 0.919 |

---

## Training runs

Continue until **run 10**, or until shaped ≥ 0.970 for 2 consecutive epochs.

### Run 6 — `oversample_cluster` reasoning ×2 — COMPLETE
- Base: `checkpoints/run4_e4.pt` (shaped 0.943)
- Corpus: `training/corpus/run6_corpus.txt` (13.65 MB)
- Result: E3 best (shaped 0.916, loops 2). Success criteria NOT met — no arithmetic breakthrough, shaped below 0.943. Dose approach exhausted: ×4 bleed, ×2 insufficient.
- Notable: German dative "über dem Berg" appeared spontaneously at E3.
- Log: `training/logs/run_6_train.log` | Report: `training/logs/run_6_report.md`

### Run 7 — `teacher_student_drill` arithmetic — COMPLETE
- Base: `checkpoints/run4_e4.pt` (shaped 0.943, best overall)
- Corpus: `training/corpus/run7_corpus.txt` (13.43 MB, 24,829 files)
- Intervention: 12 arithmetic drill files generated via DeepSeek in direct probe format (what is X plus X? → X plus X is Y.); reasoning section 108→120 files, no oversampling
- Justification: existing reasoning files use multi-modal "Teach me about..." format — format mismatch with probe. Drill files directly train the expected Q&A pattern.
- Log: `training/logs/run_7_train.log` | Report: `training/logs/run_7_report.md`
