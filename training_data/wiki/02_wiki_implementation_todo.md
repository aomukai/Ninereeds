# Wiki Implementation TODO

Active working queue for the wiki corpus.

This file is the **single active todo list** for wiki work.
Do not use it as a history log.
Completed batches and corpus-state notes belong in `training_data/wiki/01_CORPUS_STATUS.md`.

Use this file together with:
- `training_data/wiki/01_CORPUS_STATUS.md` — history, status, and cleanup notes
- `training_data/wiki/wiki_category_backlog.md` — strategic backlog and dependency map
- `training_data/wiki/level1_finish_and_level2_start_plan.md` — trunk cleanup order and overlap hotspots
- `training_data/phase 1 to 5/rewritten/missing_curriculum_terms.md` — wiki-to-curriculum anchor gaps

---

## What this file is for now

The current job is **gap filling for comprehension**.
The goal is not to add random new material.
The goal is to identify what the dragon must already understand in order to learn the existing wiki cleanly.

That means prioritizing:
1. dependency coverage
2. trunk-file ownership cleanup
3. anchor-gap logging
4. overlap reduction
5. only then broader Level 2 expansion

---

## Operating rules

- Keep this file focused on active unchecked work.
- When a task is completed, check it off here and move the result summary into `01_CORPUS_STATUS.md`.
- If a task reveals more work, add the follow-up here as a new unchecked item instead of burying it in prose elsewhere.
- Prefer dependency and comprehension fixes over decorative expansion.
- Prefer one canonical concept home whenever possible.

---

## Current active queue

### A. Build the dependency picture first

1. [ ] Create a corpus-wide dependency ledger from `wiki_category_backlog.md`
   Notes:
   - Extract every `Depends on:` item.
   - Normalize dependency terms so equivalent concepts map to the same canonical home.
   - Mark each dependency as one of: `covered in wiki`, `covered in phase 1–5 only`, `missing`, or `unclear ownership`.

2. [ ] Identify comprehension-critical missing or weak prerequisites
   Notes:
   - Focus on concepts that many files depend on, not one-off curiosities.
   - Separate true missing anchors from wording-only issues.
   - Record curriculum-anchor needs in `missing_curriculum_terms.md` when the issue is not best solved inside the wiki.

3. [ ] Produce a ranked gap list for the wiki corpus
   Notes:
   - Rank by how many files depend on the concept and how central the concept is to understanding the corpus.
   - Prefer broad prerequisites before narrow domain details.

### B. Finish the Level 1 trunk pass

4. [ ] Audit `logic_entries.md` for dependency ownership and overlap
   Notes:
   - Check overlap with time, social/pragmatic files, and abstract operators.
   - Focus especially on whether the file is carrying concepts that should live elsewhere.

5. [ ] Audit `STEM_entries.md` for dependency ownership and overlap
   Notes:
   - Check overlap with verbs, sensory files, body-state files, and weather/light/state-change files.
   - Keep it a compact bridge file, not a catch-all.

6. [ ] Audit `time_entries.md` for sequence-language ownership
   Notes:
   - Check overlap with `logic_entries.md` and `storytelling_and_narrative_structure_entries.md`.

7. [ ] Audit `space_entries.md` for shape/measurement overlap
   Notes:
   - Check overlap with `mathematical_concepts_entries.md` and `measurement_and_comparison_entries.md`.

8. [ ] Audit `verbs_entries.md` for duplicate specialist ownership
   Notes:
   - Keep high-frequency general verbs.
   - Move or trim specialist verbs where a better canonical home already exists.

9. [ ] Audit `mathematical_concepts_entries.md` for concept-only scope
   Notes:
   - Keep this file concept-language only.
   - Avoid drift into problem-solving explanation or extra spatial ownership.

10. [ ] Audit `mathematical_problems_entries.md` for Level 1 register and grounded prerequisites
    Notes:
    - This is the trunk file most likely to need real rewriting.
    - Check difficulty, prose simplicity, and dependency grounding.

11. [ ] Audit `body_parts_entries.md` for anatomy vs body-state / health drift
    Notes:
    - Keep ordering broad-to-narrow.
    - Trim entries that belong more naturally in body-state or wellness files.

### C. Gap filling after the trunk pass

12. [ ] Review `foods_vegetables_entries.md` as the first non-trunk cleanup file
    Notes:
    - This was already called out as a still-worth-a-pass file.
    - Use it as the first test case after the trunk audit.

13. [ ] Run a corpus-wide contrast and dependency cleanup pass
    Notes:
    - Verify that new or revised contrasts still point to grounded concepts.
    - Confirm that dependency fixes did not introduce duplicate anchor homes.

14. [ ] Reconcile documentation after the gap-filling batch
    Notes:
    - Update `01_CORPUS_STATUS.md` with completed work.
    - Keep `start.md` and planning docs aligned with the current two-file workflow.

---

## Deferred until the comprehension pass is stable

- Level 2 branching and richer snowflake expansion
- `00_ideas.md` connective-tissue batch
- New category creation unless the dependency audit proves it is necessary

---

## Good stopping condition for the current phase

This phase is in good shape when:
- the dependency ledger exists
- the trunk files have been audited
- the highest-value prerequisite gaps are either filled or explicitly logged
- `missing_curriculum_terms.md` contains the curriculum-side anchor gaps that should not be solved ad hoc in the wiki
- `01_CORPUS_STATUS.md` reflects the completed cleanup work
