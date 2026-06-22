---
name: Language curriculum — lang_3d complete
description: Multilingual curriculum status as of 2026-05-14; lang_1/2/3a/3b/3c/3d all done
type: project
originSessionId: c9c3642f-dfeb-42e8-8b9e-8925acc16fc3
---
lang_1 is complete as of 2026-05-11.

**What:** One file per allowlist word in training_data/lang/lang_1/. Each file has 4 lines: English, German, Japanese, Chinese. Simple category/classification grounding sentences per POS template (noun/verb/adjective).

**Why:** First level of a multilingual curriculum for Ninereeds. Provides cross-lingual grounding for every concept in the allowlist.

**How to apply:** lang_1 is done — next curriculum work is lang_2 generation. Templates are ready at training_data/lang/level_2a/b/c_templates.md. A DeepSeek session is needed to generate the actual files.

**Lang_2:** Complete (archived, committed).

**Lang_3c (2026-05-14):** Complete. 99 files in training_data/lang/lang_3/ covering reflexive, agentive_benefactive, and receptive_benefactive patterns for 47 verbs. Script: meta/scripts/lang3c.py (plan→gen flow identical to lang2.py). Jobs: lang_3_jobs.jsonl; planned: lang_3_planned.txt.

**Lang_3a (2026-05-14):** Complete. 31 files in training_data/lang/lang_3a/. Double-object and prepositional dative for 12 both-verbs; prepositional-only for 7 Latinate verbs. Script: meta/scripts/lang3ab.py.

**Lang_3b (2026-05-14):** Complete. 12 files in training_data/lang/lang_3b/. Every sentence has dative IO + genitive possessor on DO. Same script: lang3ab.py.

**Lang_3d (2026-05-14):** Complete. 400 files in training_data/lang/lang_3d/. Tiny parallel stories (6-10 sentence groups, EN/DE/JP/ZH) integrating all 6 Level-3 constructions naturally within scenes. Script: meta/scripts/lang3d.py (plan→gen, two-phase). Plans: lang_3d_plans.jsonl. Construction coverage: dative_double_object 194, agentive_benefactive 163, reflexive 160, dative_prepositional 133, receptive_benefactive 78, dative_genitive 73. 17 settings. 400/400 files verified: Japanese script throughout (no romaji), German Perfekt+V2+case correct.

**Lang_3 COMPLETE.** All four sub-levels (3a=83 files, 3b=33 files, 3c=99 files, 3d=400 files) are done and committed. Total lang_3: 615 files.

**Full lang curriculum COMPLETE:** lang_1 + lang_2 + lang_3 (all sub-levels). Total corpus volume is adequate for Ninereeds to encounter Level-3 constructions in varied contexts.

**Generator:** meta/lang_gen.py — resumable, skips existing files, batches 10 words per API call, DeepSeek V4 Flash via OpenRouter. max_tokens=8192 (some batches like "see/seek/seem" use ~8k tokens). stdout reconfigured to UTF-8 to handle CJK in log output on Windows.

**Cleanup done:**
- Removed stray filelist.txt entry from allowlist.txt
- Fixed 14 truncated -ness words (brightnes → brightness, etc.) in allowlist and files
- Removed especial from allowlist and deleted especial.md
- Rewrote rudeness.md (model had hallucinated "A rudenes is a type of plant")
- ~76 numbered files (_3 through _12) left in place — all contain valid content, kept as corpus variants
