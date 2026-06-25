# Memory Index

**Authoritative copy. Read and write here only.**
Both Windows and Linux use the same physical directory — no syncing needed.

---

- [User profile](user_profile.md) — Language teacher; research collaboration not task queue; document rationale not just state; context loss is costly
- [Ninereeds project overview](project_ninereeds_overview.md) — What Ninereeds is: small Hebbian-trained AI, quality gates matter more than usual because no error averaging from scale
- [Corpus structure](project_corpus_structure.md) — training_data/ layout: phases, wiki, stories, reasoning, philosophy
- [Campaign 13 & 14 status](project_campaign_status.md) — C13 complete (0.925); C14 complete (A wins, bridge-before-grammar); C15 design documented in todo.md; see handoff_2026-06-18.md
- [2026-06-23 handoff](handoff_2026-06-23.md) — C16A complete; corpus cleaned (28 buckets, unsorted empty); ready for weekend training; aug_done.txt path staleness issue documented
- [Brain map graph format](feedback_brain_map_graph.md) — 3D HTML graph is primary eval output; probe→hubs→graph is the standard sequence; open _graph.html in browser
- [C16B supplement design](project_c16b_supplements.md) — 5 diagnosed issues (food spine, nature spine, emotion grounding, action spine, boundary vs negation); file naming, validation rules, training chain
- [CKS education pipeline](project_cks_pipeline.md) — Phases 1–3 complete; Phase 4 (dialogue gen) is next; 301 nodes in phase2_merged.jsonl; runner to build: phase4_gen.py
- [Teaching stories design](project_teaching_stories.md) — Bird's eye / omniscient narrator; same story localised into EN/DE/JP/ZH; grammar complexity by tier (1=picture book, 4=2nd grade); replaces old B/D/E phase files
- [Teaching stories rationale](project_teaching_stories_rationale.md) — WHY: omniscient narrator, grammar tiers, localisation not translation, same story in all languages, relationship to grounded_stories
- [Worker delegation architecture](feedback_delegation_architecture.md) — Bulk file work goes to DeepSeek; Claude handles planning and verification only
- [Tool index and platform rules](feedback_platform_tools.md) — opencode = Linux only; direct API runners work on Windows+Linux; see CLAUDE.md for full index
- [Hard constraints](feedback_hard_constraints.md) — Never modify bdh.py or core/; no training until audit is GO; only close todo items with file-level evidence
- [Memory location rule](feedback_memory_dual_write.md) — Write all memories to claude/ only; both OSes share the same physical directory; platform-local path is irrelevant
- [Localization prompt design](feedback_localization_prompt_design.md) — "localise naturally" not "translate"; preserve meaning not wording; anti-calque examples required in JP/ZH prompts
- [Eval philosophy](feedback_eval_philosophy.md) — loss curves irrelevant; brain_map (MRI) + shaped score are the real diagnostics; run both probe sets after each block
- [Language rotation design](project_language_rotation.md) — Vignettes rotation (EDJC/DJCE/JCED/CEDJ) was deliberate fix for EN/DE positional advantage; validated by Block 4 eval (ZH 0.998 > EN 0.997); extend to boolean_stories, philosophy, and manifest ordering before next run
- [Dedicated training machine](project_dedicated_training_machine.md) — 2× RTX 3060 headless build; parts ~July 2026, target August 2026; enables parallel runs and concurrent eval
- [JP-specific corpus (future)](project_jp_corpus.md) — if C15 confirms JP gap is not rotation-related; sources: imabi.org, guidetojapanese.org; pedagogical register retains particles/subjects explicitly
