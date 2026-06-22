---
name: project-campaign-status
description: C13 done (0.925); C14 done (A wins); C14c corpus ready to train — vignettes + grounded story scale-up complete
metadata:
  type: project
---

Campaign 13 complete. Best checkpoint: `checkpoints/c13_Phase_C_winner.pt` shaped=0.925.

**Campaign 14 — COMPLETE (2026-06-18):**
- Variant A wins (bridge-before-grammar). See `training/logs/campaign_14_reports/02_bridge_after_grammar.md`.
- Bridge expanded to 234 files; teaching stories annotated (5006 × case-role brackets).

**Campaign 14c corpus — READY TO TRAIN (2026-06-20):**
New additions since C14b:
- Vignettes (2048 files): sentence-rotation paraphrase, 5 syntactic angles × 4 langs, Block 4 = resultative
  - Manifest: `training/corpus_admin/campaign14_blocks/c14_05_vignettes.txt`
  - Corpus text: not yet built — run `build_training_corpus.py` before training
- Grounded stories (2988 files, up from 780): 747 stories × 4 langs; 10 new groups (mill, workshop, market, hill, etc.)
  - Manifest: `training/corpus_admin/campaign14_blocks/c14_03_grounded_stories.txt` (updated)
  - Corpus text: `training/corpus/c14_03_grounded_stories.txt` — 3.20 MB, clean

**Hypothesis for C14c:** vignettes improve grammar μ (sentence-rotation forces semantic invariant extraction);
grounded story scale-up improves causal reasoning and multilingual coverage.

**Block order (all --no-shuffle):** language core → arithmetic bridge → grounded stories → reasoning → vignettes

**If C14c improves language but leaves grammar still weak:** scale to 150M; at that scale long-form content
may be more appropriate than short stories.

**CKS education pipeline (Campaign 16 prep) — COMPLETE (2026-06-18):**
- All 418 dialogue files generated; `training/corpus_admin/campaign16_manifest.txt` verified.
- Waiting for C14c to complete before starting C15/C16.

**Why:** C14 confirmed bridge-first ordering. C14c adds variety of situation (vignettes) and scale of
narrative grounding (750 stories vs 195). These are the two hypothesized gaps from brain_map analysis.

**How to apply:** Check `ps aux | grep train.py` before launching. Build vignettes corpus text first
(it's the only block not yet built). Base checkpoint: check `checkpoints/` for best from C14a/b runs.
