# History

Procedural log of completed work. Newest at top.
When a task is done: delete from `todo.md`, add an entry here.

---

## 2026-06-28

**Campaign 17 closed — contrast helped, global repair remained unstable** — C17 tested full mixed kernel training, dependency/curriculum ordering, contrast-angle ordering, and several boundary repair schedules. Full mixed and full curriculum runs failed. Compact 1,200-concept training recovered useful behavior, with the contrast-angle branch winning: `core/c17_contrast_angle_1200_e4.pt`, default eval 5/7, avg 0.905. This checkpoint is the protected C17 best. Report and handoff: `training/logs/campaign_17_reports/00_prelaunch.md` and `training/logs/campaign_17_reports/01_handoff.md`.

**C17 ordering result** — Dependency/curriculum order improved over full mixed training but underperformed contrast-angle ordering. Best sorted branch: `core/c17_ladder_1200_e2.pt` / `e3`, 4/7 avg 0.857. Best contrast branch: `core/c17_contrast_angle_1200_e4.pt`, 5/7 avg 0.905. Interpretation: maximum contrast inside small chunks reduced concept mixing better than dependency order alone.

**C17 repair result** — Boundary repair showed that concept-local correction can move target probes but tends to damage default grounding. V2 damaged-concepts-only repair reached boundary_v2 7/7 avg 0.964 but dropped default avg to 0.869, below the protected best. Larger contrast-review repair did not recover the default gate. Micro v3 repair variants all landed at default 4/7 avg 0.857 and boundary_v2 2/7 avg 0.607. Decision: do not promote repair branches; keep `core/c17_contrast_angle_1200_e4.pt`.

**Tutor-loop direction documented** — Added `training/pipeline/tutor_loop.md` for a concept-card PPP tutor loop with declared prerequisites, diagnostic vs training answers, block-size budgets, free-practice validation, SRS boxes, protected anchors, and answer complexity ladder. This became the planned next design path after C17: move from hand-built global repair files to adaptive per-concept teaching via a Mommy Says machine.

## 2026-06-27

**C17 mixed JSONL assembled** — Added `meta/scripts/mix_jsonl.py` for fixed-ratio prompt/completion JSONL interleaving. Built `training/corpus/kernel_c17_mixed.jsonl` with 249,482 examples from converted redesign, gap-fill, and identity/control data. Identity/control share is 12.000% via 32 deterministic oversample cycles, interleaved throughout rather than appended. Report: `training/corpus/kernel_c17_mixed_report.md`. Prelaunch commands recorded in `training/logs/campaign_17_reports/00_prelaunch.md`.

## 2026-06-26

**Campaign 17 opened — kernel corpus and chat-capable core** — C17 replaces the old C16A/B/C augmentation roadmap. Kernel path chosen: preserve `training_data/redesign/` untouched, convert useful redesign files into `training_data/kernel_from_redesign/`, generate missing kernel angles into `training_data/kernel_gap_fill/`, and build a separate high-ratio identity/control corpus from `identity.md`. Added tools: `meta/scripts/generate_kernel_corpus.py`, `meta/scripts/convert_redesign_to_kernel.py`, `meta/scripts/build_kernel_vocab_seed.py`, `meta/scripts/build_kernel_gap_seed.py`, `meta/scripts/supervise_kernel_gap_fill.sh`, `meta/scripts/audit_identity_corpus.py`.

**Kernel conversion baseline built** — Converted redesign corpus into kernel source format. Source files seen: 66,536. Files written: 66,507. Invalid skipped: 29. Validated output: 66,495 kernel files. Training JSONL built at `training/corpus/kernel_from_redesign.jsonl` with 83,880 examples. Report: `training/corpus/kernel_from_redesign_report.md`. Decision: rewrite/convert existing redesign material first; generate only missing angles instead of regenerating the full vocabulary from scratch.

**Kernel gap-fill generation launched under supervisor** — Built full allowlist seed `training/corpus_admin/kernel/kernel_full_words.jsonl` with 5,156 records, then gap seed `training/corpus_admin/kernel/kernel_gap_words.jsonl`. Started all three DeepSeek endpoints via supervisor: OpenRouter, DeepSeek direct, and NVIDIA NIM. Output target: `training_data/kernel_gap_fill/`. Supervisor checks every 30 minutes and will validate/build `training/corpus/kernel_gap_fill.jsonl` after completion.

**C17 gap-fill corpus completed and built** — Completed all 5,156 gap concepts with 47,865 validated source files under `training_data/kernel_gap_fill/`. Reconciled stale failed markers and stale claims to zero. Built `training/corpus/kernel_gap_fill.jsonl` with 135,664 examples and lowercase user copies. Report: `training/corpus/kernel_gap_fill_jsonl_report.md`.

**Identity corpus spec written** — Added `identity.md` for a dedicated 160–240 file identity/control corpus under `training_data/kernel_identity/`. Patched JSONL builder to support explicit `--repeat-identity-path`, so `kernel_identity/` can be oversampled separately from concept corpora. Added `meta/scripts/audit_identity_corpus.py` to catch identity contradictions and verbose contrast answers before training.

**C17 identity corpus generated and built** — Generated `training_data/kernel_identity/` from `identity.md` using DeepSeek direct. Output: 219 audited Markdown files across core, contrast, limits, knowledge, senses, language, chat_control, correction, unknowns, and multi_turn groups. Audit passed with `meta/scripts/audit_identity_corpus.py`. Built `training/corpus/kernel_identity.jsonl` with 939 examples using `--repeat-identity 3`, explicit `--repeat-identity-path training_data/kernel_identity/`, and lowercase user copies. Report: `training/corpus/kernel_identity_jsonl_report.md`.

**Kernel proof-of-concept trained** — Small 50-concept JSONL kernel experiment showed that prompt/completion JSONL with masked instruction loss is better than concatenated text. Best current kernel proof: `core/kernel_e1_focus_repair.pt`, strict grounding eval 5/7, avg score 0.905. It outperformed `core/kernel_e4_focus_repair.pt` in the focused repair comparison. This is not the final C17 model; it is the proof that the kernel method is viable.

## 2026-06-25

**Brain trace/atlas tooling added** — Extended brain map tooling with trace/atlas outputs for next-move diagnostics. New workflow maps concepts, cluster structure, cross-category edges, weak concepts, overconnected hubs, and clickable atlas views. Key outputs include `training/logs/brain_maps/c16_e4_redesign_current_atlas.html` and `training/logs/brain_maps/c16_e4_redesign_current_trace_report.md`.

**C16 E4/E5 rescanned with new trace tooling** — E4 remained the practical C16 winner over E5. New trace exposed that identity is structurally fuzzy despite usable behavioral answers: identity concept cosine 0.610 and Jaccard 0.463, far weaker than most concept categories. This directly motivated the C17 identity/control corpus.

## 2026-06-22 (continued)

**Campaign 16 complete — concept anchoring winner E4** — C16 trained EN-only redesign concept anchoring from fresh init on `training/corpus/redesign_c16.txt` (34,645 files: 33,966 concept + 679 identity insertions). Winner: `core/c16_redesign_e4.pt`, promoted target `checkpoints/c16_concept_anchoring_winner.pt`. E4 had shaped 0.996, flags 0, chat 9/12. E5 regressed on 2/3 signals and was stopped. Report: `training/logs/campaign_16_reports/01_c16_concept_anchoring.md`.

**C16 findings** — Boundary/I-do-not-know behavior crystallized first and strongest. Concrete objects outperformed abstract categories. Identity was behaviorally usable but structurally weak, routed through general hubs rather than a strong identity cluster. C16 confirmed the recipe shift: EN-only, semantic bucket ordering, identity interleaving, and multiple angles per word allowed useful learning beyond E2/E3 where prior multilingual campaigns had peaked.

**C16 training launched** — `python -u train.py --phase 0 --corpus-file training/corpus/redesign_c16.txt --output core/c16_redesign_e1.pt --epochs 1 --batch-size 4 --no-shuffle --log-vram`. Fresh init, sequential order, 4987 steps, 25M model. Loss at step 100: 2.2264 (better than prior killed run at 2.4516 — organized buckets showing effect). Log: `tmp/c16_e1_train.log`. PID 2564363.

**Bucket expansion** — 10 → 24 semantic buckets in `training_data/redesign/words/`. New tool: `meta/scripts/rebucket.py`. Moved 10,044 files. 14 new buckets: movement, actions, emotions, social, states, cognition, communication, colors, shapes, materials, quantities, space, time, language. 23,162 remain in unsorted (genuinely abstract words). Key conflict resolution: crane → animals (bird not tool).

**Corpus rebuilt for C16** — 34,645 files (33,966 concept + 679 identity insertions). 24-bucket order: animals→nature→body→food→household→people→places→clothing→tools→movement→actions→emotions→social→states→cognition→communication→colors→shapes→materials→quantities→space→time→properties→language→unsorted. Identity interleaved every 50 concept files (56.6×). 0 format errors. Output: `training/corpus/redesign_c16.txt`, 4.87 MB.

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
