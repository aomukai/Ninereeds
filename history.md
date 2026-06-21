# History

Procedural log of completed work. Newest at top.
When a task is done: delete from `todo.md`, add an entry here.

---

## 2026-06-22

**Corpus redesign complete (Tier 1)** — 33,600+ files generated across ~5,100 words from `inventory/allowlist.txt`. Three parallel sources (OpenRouter, DeepSeek direct, NVIDIA NIM) using atomic claim mechanism. Output: `training_data/redesign/words/` organized by semantic bucket (animals, body, food, household, nature, people, actions, properties, space, time, unsorted). 50 failures queued for retry. Key design: EN-only, concept anchoring, variable-length files, "I don't know" as first-class response.

**Identity corpus hand-crafted** — `training_data/redesign/identity/`: 12 files covering name/what/capability/knowledge/origin/limits/feelings/language/contrast/greetings/farewells/clarification. Ninereeds identity anchoring, self/other distinction, greeting responses.

**New tools** — `meta/scripts/angle_gen.py` (3-source parallel generator with atomic claims, rate limit retry, bucket routing), `meta/scripts/angle_aug.py` (question-form augmentation waves 1–3), `meta/scripts/eval_concept.py` (chat-style comprehension eval), `meta/scripts/angle_gen_monitor.sh` (30-min watchdog).

**Eval methodology redesigned** — Runbook updated: epoch loop is train→brain scan→eval_concept→chat session→compare. Winner = last epoch before regression. Chat impression is primary signal, not loss or shaped score.

**chat.py improved** — Dark mode, max_new_tokens 120→200, mojibake stripping.

## 2026-06-21 (continued)

**C15 complete — all block reports written** — Blocks 2–5 reports written at `training/logs/campaign_15_reports/02–05_*.md`. Key findings consolidated: arith_jp trajectory 0.984→0.990→0.937→0.9994; vignettes confirmed 1-epoch cap (−0.077/epoch); education block restores arith_jp (not damaging multilingual μ — K-8 localization gate cleared); K-8 placed last was the right call (arith_jp recovery at end).

**Scaffolding restructured** — `training/pipeline/runbook.md` created (pre-launch checklist + procedure). `index.md` stripped to pure pointer index. `todo.md` now delete-on-done with history in `history.md`.

---

## 2026-06-21

**Docs restructured** — `index.md` rewritten as lean session-start + campaign checklist. `todo.md` redesigned as live task list (delete-on-done). `training/docs/pipeline.md` repurposed as automation spec for `campaign_runner.py`. `training/docs/training.md` stripped of duplicate findings; Step 7/8 contradiction (shaped vs brain_map priority) resolved. `docs/curriculum_topology.md` C15 section updated with actual results.

**C15 Block 4 (vignettes) complete** — E1 winner: arith_jp 0.937, shaped 0.987. Key finding: arith_jp collapses −0.08 per epoch (0.937→0.860→0.781). Vignettes must be capped at 1 epoch in all future campaigns. Report pending.

**C15 Block 3 (reasoning/arithB) complete** — E1 winner: arith_jp 0.990, shaped 0.941. E2 showed rule_application spike (0.921) but cost arith_jp (−0.009). Report pending.

**C15 Block 2 (arith+grounded) complete** — E1 winner: arith_jp 0.984, shaped 0.976. E1 winner pattern confirmed for focused blocks (<1000 files). Report pending.

**C15 Block 1 (language core) complete** — E2 winner: arith_jp 0.987, shaped 0.958. EDJC rotation confirmed: arith_jp at language-block stage exceeds C14c peak (0.912) which came 4 blocks later. Report: `training/logs/campaign_15_reports/01_c15_language.md`.

**OOM fix for memory-constrained training** — `--batch-size 1 --grad-accum-steps 2 --adam8bit` + `PYTORCH_ALLOC_CONF=expandable_segments:True` reduces peak VRAM by ~350 MB. Required when mnm.exe holds 7.4 GB VRAM on training GPU. Embedded in `c15_pipeline.py`.

**7 boolean story files fixed** — `bool_meow_3`, `bool_rude_3`, `bool_sway_3`, `bool_tackle_2`, `bool_peaceful_2`, `bool_cane_3`, `bool_swish_3`. Missing `[Ninereeds]` blocks added. Corpus rebuilt: 42,021/42,021 files, 0 skipped.

---

## 2026-06-20

**C15 corpus built** — `training/corpus/campaign15_full.txt`: 42,021 files, 54.89 MB, 0 skipped. EDJC rotation applied to all multilingual blocks. Thinking block corpora also built (arith+grounded, reasoning, vignettes, education).

**C14c complete** — Winner: `checkpoints/c14c_winner.pt` = `core/c14c_vignettes_e2.pt` (shaped 0.989, EN 0.996, DE 0.983, JP 0.980, ZH 0.997). Brain scan overturned E3: spatial after-hub collapse + arithmetic_grounded loss in E3 outweighed 0.001 shaped gain. Report: `training/logs/campaign_14_reports/03_campaign14c.md`.

**Grounded stories expanded** — 195 → 747 stories (2,988 files). New characters: Mei, Yun, Riku, Stefan, Hana, Owen, Clara, Vern, Dr. Lena, Dr. Anand. New locations: The Mill, Vern's Workshop, The Hill, The Root Cellar.

**Vignettes corpus built** — 2,048 clean files from 2,920 generated (872 failed audit, deleted). Generator: `meta/scripts/vignette_gen.py`. Manifest: `training/corpus_admin/campaign14_blocks/c14_05_vignettes.txt`.

---

## 2026-06-18

**CKS Education corpus complete** — 418 `[user]/[Ninereeds]` dialogue files. Preschool (156 files × 4 langs) + K-8 (262 files, EN only). Manifest: `training/corpus_admin/campaign16_manifest.txt`. Report: `training_data/ninereeds_cks_curriculum.md`.

**Bridge corpus complete** — 352 files total. Extended with always-dative prepositions (80 files), dative pronouns (32 files), NOM/ACC isolation (20 files), 4-case permutations (120 files). Original 100 files retrofitted (named chars → generic NPs). Path: `training_data/01_language/bridge/`.

**Arithmetic bridge Phase B complete** — 5 paraphrase files (`p01–p05`). Generator: `meta/scripts/arith_gen.py --phase b`.

**Thinking probe set built** — `training/corpus_admin/probe_sets/thinking.jsonl`: 94 probes, 14 categories. Covers arithmetic ×4 langs, paraphrase, grounded, identity, comparison, successor, zero, sequences, rule_application, contrastive, grounded_causal.

---

## 2026-06-07 and earlier

**C14 language campaign complete** — Variant B (bridge after grammar) won over Variant A. Winner: `checkpoints/c14_winner.pt` (shaped 0.934). Report: `training/logs/campaign_14_reports/`.

**Arithmetic bridge Phase A complete** — 15 compact 4-lingual drill files (`c01–c15`). Peano-ordered. Generator: `meta/scripts/arith_gen.py --phase a`.

**Language probe set built** — `training/corpus_admin/probe_sets/language.jsonl`: 104 probes, 16 categories.

**Teaching stories complete** — 5,006 stories across 4 tiers, 50 domain buckets. Generator: `meta/scripts/story_gen_v2.py`. Boolean stories: 800 files. Path: `training_data/01_language/teaching_stories/`.

**Campaign 13 complete** — Bridge → Phase A → Phase B (agents/social) = shaped 0.925. Winner: `checkpoints/c13_Phase_C_winner.pt`. Established: B/D/E absorption failure in static-property format; bridge as corrective layer (not cold-start primer); Phase A ceiling confirmed at 0.925.

**Lang curriculum complete** — lang_1 through lang_5, all four languages. ~12,000 files. Path: `training_data/01_language/lang/`.

**Triplet stories localized** — 1,345 EN × 4 languages = 5,380 files. Path: `training_data/01_language/triplet_stories/`.

**Philosophy corpus localized** — 144 files, 4-language tag format. Path: `training_data/05_philosophy/`.

**Reasoning corpus localized** — 27 EN × 4 languages = 108 files. Path: `training_data/02_thinking/reasoning/`.
