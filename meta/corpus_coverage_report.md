# Corpus Coverage Report
Generated: 2026-05-04

## File Counts

| Directory | Files | Sample |
|---|---|---|
| phases/phase_1 | 1229 | phase_1_001.md |
| phases/phase_2 | 343 | phase_2_001.md |
| phases/phase_3 | 602 | phase_3_001.md |
| phases/phase_4 | 91 | phase_4_01.md |
| phases/phase_5 | 189 | phase_5_01.md |
| phases/phase_6 | 1151 | phase_6_001.md |
| wiki/wiki_1 | 111 | abstract_operators_entries.md |
| wiki/wiki_2 | 12 | communication_acts_and_language_level2.md |
| wiki/wiki_3 | 3 | emotions_level3.md |
| wiki/wiki_4 | 3 | emotions_level4.md |
| philosophy | 12 | ninereeds_dialogues_cat10.md |
| reasoning | 27 | 00_bridge_word_to_symbol.md |
| triplet_stories/tier_1 | 10 | animals_and_nature.md |
| triplet_stories/tier_2 | 10 | animals_and_nature.md |
| triplet_stories/tier_3 | 10 | animals_and_nature.md |
| triplet_stories/tier_4 | 10 | animals_and_nature.md |

## Dependency Graph

- Total registered nodes: 2086
- Unique target words covered: 1144

## Phase_5 Gap Analysis

Phase_5 has a critical structural hole:

| Range | Files | Status |
|---|---|---|
| phase_5_001 – phase_5_046 | 46 | Present — action sequences |
| phase_5_047 – phase_5_1858 | 1812 | **DELETED** — social/emotional vocab, not regenerated |
| phase_5_1859 – phase_5_2001 | 143 | Present — backfill regen (Format A verbs/nouns) |

The 1812 deleted files were removed because they were wrong format. Only 143 replacement entries have been generated (the 353-word backfill regen, with entries distributed across phases 2-6). Approximately 1669 social/emotional/relational vocabulary entries are absent.

## Vocabulary Gap (from training_activation_audit.md)

- Total high-priority audit words: 120
- Covered in dependency graph: 16 (13%)
- On disk but not in graph: 35 (29%)
- **Truly missing (no file anywhere): 69 (58%)**

### 69 words with no phase file on disk:

now, little, also, everyone, alone, picture, special, doing, easier, watches, feelings, wooden, best, almost, clearly, looking, taking, blows, class, common, toys, opposite, times, sister, talking, choice, here, running, happening, meals, favorite, safely, single, questions, ways, giving, brother, bad, healthy, party, facts, starting, helping, hiding, grabs, homework, classroom, problems, shoes, trip, likes, gently, smiles, pencil, activity, breakfast, triplets, maintaining, kinds, stuck, gentle, ahead, decides, however, least, label, since, perhaps, therefore

### 35 words on disk but not registered in graph:

Present in phase files but missing from dependency_graph.json — graph needs updating after any backfill verification pass.

## Phase Format Spot Check

| Phase | [user]/[Ninereeds] blocks | Opens with "This is X." | Issues |
|---|---|---|---|
| phase_1 | 4/4 ✓ | Yes ✓ | None |
| phase_2 | 4/4 ✓ | Yes ✓ | None |
| phase_3 | 4/4 ✓ | Yes ✓ | None |
| phase_4 | 1–2 per file ✓ | Yes ✓ | Correct — manifest specifies 1-2 blocks |
| phase_5 | 1 per file (action seqs) | Yes ✓ | Backfill entries use Format A, not Format B — minor inconsistency vs manifest |
| phase_6 | 4/4 ✓ | Yes ✓ | None |

## Summary

**Solid:** Phases 1-4 and 6 are complete and correctly formatted. Philosophy (12), reasoning (27), and triplet_stories (4×10=40) are all in good shape. Wiki_1 has 111 articles.

**Thin:** Wiki levels 2-4 are barely started (12/3/3 files). Only a handful of topics have depth beyond level 1. The dependency graph only covers about 2086 of ~3600+ total corpus files.

**Missing:** Phase_5 is the critical gap. 1812 social/emotional vocabulary files were deleted and only 143 backfill entries have replaced them. Approximately 1669 social/emotional relational vocabulary entries (family roles, emotional states, daily-life actions) are absent from the curriculum. Additionally, 69 of 120 high-priority audit words have no phase grounding file at all — these are common words (now, little, also, everyone, class, sister, brother, etc.) that appear in later corpus tiers but are undefined at the foundational phase level.

**Training readiness:** NOT READY. The harness already shows `corpus_v1_0_not_complete`. The phase_5 social/emotional vocabulary layer needs to be rebuilt before training activation.
