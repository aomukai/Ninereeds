---
name: project-language-rotation
description: Language rotation design principle — EN/DE positional advantage, vignette fix, and planned corpus extension
metadata:
  type: project
---

Vignettes were intentionally designed with across-file language rotation (EDJC/DJCE/JCED/CEDJ) to counter EN/DE positional advantage over JP/ZH in Hebbian co-firing. Validated by Block 4 eval: ZH 0.998, EN 0.997, DE 0.985, JP 0.979 — ZH edge over EN after rotation training, which would not happen if CJK were structurally disadvantaged.

**Why:** In Hebbian learning, the language that appears first in a training sequence co-fires with more context tokens and receives stronger weight reinforcement. Always-first EN/DE was suppressing JP/ZH circuit formation.

**How to apply:** Extend rotation to the rest of the corpus before next training run:
- `boolean_stories/` (800 files) — internal EN/DE/JP/ZH blocks, need within-file reorder → DeepSeek bulk job
- `05_philosophy/` (144 files) — internal [STATEMENT_EN/DE/JA/ZH] tag blocks, need within-file reorder → DeepSeek bulk job
- `lang_1–5/`, `triplet_stories/`, `grounded_stories/`, `reasoning/` localized — separate files per language, need manifest interleaving → scripting only (build_training_corpus.py)
- `vignettes/` — already rotated, no change needed

**Decision:** Brain_map after C14c Block 5 to confirm JP multilingual μ gap. If confirmed, do manifest interleaving first (easy), then boolean/philosophy bulk reorder before next training run. See [[project-c14c-campaign]].
