# Wiki Corpus Ranked Gap List

Generated from analysis of:
- `dependency_ledger.md` — concept grounding and ownership map
- `wiki_category_backlog.md` — category dependencies and status
- `01_CORPUS_STATUS.md` — file role groups and dependency chains
- `level1_finish_and_level2_start_plan.md` — overlap hotspots

Purpose: Prioritize gaps by how many files depend on the concept and how central it is to understanding the corpus. Prefer broad prerequisites before narrow domain details.

---

## Ranking Criteria

Each gap is scored on:

1. **Dependency count**: How many wiki files or categories depend on this concept?
2. **Centrality**: Is this concept foundational (needed for many domains) or peripheral (domain-specific)?
3. **Comprehension impact**: Would missing this concept cause cascading confusion across the corpus?
4. **Urgency**: Is this blocking the trunk audit or Level 2 expansion?

Tiers:
- **Tier 1 (Critical)**: High dependency count + high centrality + blocks comprehension
- **Tier 2 (Important)**: Medium-high dependency count OR medium centrality
- **Tier 3 (Useful)**: Lower dependency count, domain-specific, or already partially covered
- **Tier 4 (Low priority)**: Adequately grounded in curriculum, not blocking wiki work

---

## Tier 1 — Critical Gaps (Immediate Action)

These concepts are foundational and have the highest impact on corpus comprehension.

| Rank | Concept | Status | Dependency Count | Centrality | Recommendation |
|------|---------|--------|------------------|------------|----------------|
| 1 | `thing` / `object` | No wiki anchor | Very high (~50+ files) | Foundational — nearly all "what is X?" entries implicitly depend on understanding that X is a thing/object | Add entry to `abstract_operators_entries.md` or create new foundational file |
| 2 | `word` | No wiki anchor | High (~20+ files) | Foundational — communication, storytelling, logic, and language files all assume knowledge of what a word is | Add entry to `communication_acts_and_language_entries.md` |
| 3 | `sentence` | No wiki anchor | Medium-high (~15+ files) | Foundational — storytelling, communication, and logic files assume sentence-level understanding | Add entry to `communication_acts_and_language_entries.md` |
| 4 | `idea` / `thought` | Weak — only in missing_curriculum_terms.md | Medium-high (~15+ files) | Foundational — logic, learning, metacognition, opinion, and perspective files depend on it | Add entry to `logic_entries.md` |

### Why Tier 1 matters

These four concepts form the meta-layer that the corpus assumes but never explicitly teaches:
- `thing`/`object` — the universal anchor for all noun-based entries
- `word` — the building block for all language entries
- `sentence` — the structural unit for communication and story entries
- `idea`/`thought` — the cognitive unit for reasoning and reflection entries

Without these, the model may learn vocabulary but miss the structural scaffolding.

---

## Tier 2 — Important Gaps (Address During Trunk Audit)

These are ownership splits or weak anchors that should be resolved during the trunk cleanup pass.

| Rank | Concept | Status | Files Involved | Impact | Recommendation |
|------|---------|--------|----------------|--------|----------------|
| 5 | `begin` / `middle` / `end` | SPLIT ownership | logic_entries.md, storytelling_and_narrative_structure_entries.md | Medium-high — sequence concepts used in 15+ files | Resolve: storytelling owns narrative sense; logic owns abstract sequence sense |
| 6 | `eat` / `drink` / `sleep` | SPLIT ownership | STEM_entries.md, verbs_entries.md | Medium — biological vs action usage in 10+ files | Clarify: both usages intentional; STEM owns process, verbs owns action |
| 7 | `see` / `hear` / `smell` / `taste` / `touch` | SPLIT ownership | STEM_entries.md, sensory_experiences_entries.md | Medium — sense organs vs sensory description | Clarify: STEM owns organs/science, sensory_experiences owns descriptive layer |
| 8 | `past` / `present` / `future` | Potential overlap | time_entries.md, logic_entries.md | Medium — temporal vs logical uses | Recommend: time_entries owns temporal meanings; logic uses for abstract tense reasoning |
| 9 | `height` / `width` / `depth` | Potential overlap | space_entries.md, measurement_and_comparison_entries.md | Lower — 5+ files affected | Recommend: measurement owns quantities; space owns spatial dimensions |
| 10 | `full` / `empty` | SPLIT ownership | containers_and_capacity_entries.md, states_of_being_and_condition_entries.md | Lower — 5+ files | Recommend: containers owns container-specific states |
| 11 | `wet` / `dry` | SPLIT ownership | STEM_entries.md, states_of_being_and_condition_entries.md | Lower — 5+ files | Recommend: states owns condition adjectives |
| 12 | `awake` / `asleep` | SPLIT ownership | STEM_entries.md, states_of_being_and_condition_entries.md, sleep_and_rest_entries.md | Lower — 3+ files | Recommend: sleep_and_rest owns sleep context |

### Why Tier 2 matters

These are not missing concepts — they exist — but unclear ownership causes:
- Duplicate anchors (confusing for training)
- Inconsistent teaching (different files teach the same word differently)
- Trunk instability (makes Level 2 expansion risky)

Resolving these during the trunk audit prevents propagating confusion downstream.

---

## Tier 3 — Useful Gaps (Address After Trunk Audit)

These concepts have anchors somewhere but may need strengthening or verification.

| Rank | Concept | Status | Current Home | Impact | Recommendation |
|------|---------|--------|--------------|--------|----------------|
| 13 | `person` | WIKI (people_roles_entries.md) | people_roles_entries.md | Very high but covered | Verify anchor is clear and appears early in file |
| 14 | `animal` | WIKI (animals_mammals_entries.md) | animals_mammals_entries.md | Very high but covered | Verify anchor is stable and general before specific |
| 15 | `place` | WIKI (places_and_landforms_entries.md) | places_and_landforms_entries.md | High but covered | Verify anchor is clear |
| 16 | `category` | WIKI (abstract_operators_entries.md) | abstract_operators_entries.md | Medium | Entry exists; `categories_and_grouping_entries.md` now provides clearer practical anchor |
| 17 | `fire` | CURRICULUM only | phase 1 curriculum | Medium — safety-relevant | Verify curriculum anchor is solid enough for safety, cooking, weather files |
| 18 | `more` / `less` | WIKI (logic_entries.md) | logic_entries.md | Medium | Confirm grounded with concrete examples during trunk audit |
| 19 | `part` / `whole` | WIKI (logic_entries.md) | logic_entries.md | Medium | Strong coverage — verify it stays clear |
| 20 | `same` / `different` | WIKI (logic_entries.md) | logic_entries.md | Medium | Strong coverage — verify it stays clear |
| 21 | `why` / `because` | WIKI (communication, evidence files) | communication_acts_and_language_entries.md, evidence_and_justification_entries.md | Medium | Check causal connectives are explicitly taught |
| 22 | `if` / `then` | WIKI (logic_entries.md) | logic_entries.md | Medium | Verify entry is child-accessible |

### Why Tier 3 matters

These concepts are technically present but need verification:
- Are they taught early enough in their files?
- Are the definitions child-accessible?
- Do dependent files actually benefit from them?

This is housekeeping work, not gap-filling.

---

## Tier 4 — Low Priority (No Action Needed)

These concepts are adequately grounded in the phase 1-5 curriculum and do not need wiki anchors.

| Concept | Curriculum Anchor | Wiki Files Using It | Risk Level |
|---------|-------------------|---------------------|------------|
| `door` | phase 1 | home_rooms, daily_routines | Low — basic object |
| `window` | phase 1 | home_rooms, home_objects | Low — basic object |
| `table` | phase 1 | meals, home_objects, daily_routines | Low — basic furniture |
| `chair` | phase 1 | home_objects, school_life | Low — basic furniture |
| `stick` | phase 1 | play/games, tools | Low — basic object |
| `block` | phase 1 | play/games, construction | Low — toy/construction |
| `ball` | phase 1 | play/games, sports | Low — toy |
| `doll` | phase 1 | play/games, imagination | Low — toy |
| `rope` | phase 1 | play/games, tools | Low — tool/play |
| `sandbox` | phase 1 | play/games | Low — play structure |
| `seesaw` | phase 1 | play/games | Low — play structure |
| `hook` | phase 1 | tools | Low — hardware |
| `brick` | phase 1 | construction | Low — building material |
| `honey` | phase 1 | foods | Low — food item |

### Why Tier 4 is safe to defer

These basic objects:
- Are already well-grounded in curriculum
- Are not heavily depended on by wiki files for comprehension
- Would add entry bloat without improving understanding

Only add wiki anchors if a specific new file requires them.

---

## Summary Statistics

| Tier | Gap Count | Action Required |
|------|-----------|-----------------|
| Tier 1 (Critical) | 4 | Add wiki entries immediately |
| Tier 2 (Important) | 8 | Resolve ownership during trunk audit |
| Tier 3 (Useful) | 10 | Verify anchors after trunk audit |
| Tier 4 (Low priority) | 14 | No action needed |

**Total gaps identified**: 36
**Gaps requiring new entries**: 4 (Tier 1)
**Gaps requiring ownership resolution**: 8 (Tier 2)
**Gaps requiring verification only**: 10 (Tier 3)
**Gaps adequately grounded**: 14 (Tier 4)

---

## Recommended Action Sequence

### Immediate (before continuing trunk audit)

1. Add `thing` / `object` entry to `abstract_operators_entries.md`
   - Define as the general category that includes all physical items
   - Contrast: "A thing is not a feeling" or "An object is not an idea"

2. Add `word` entry to `communication_acts_and_language_entries.md`
   - Define as a unit of language with meaning
   - Contrast: "A word is not a letter" or "A word is not a sound"

3. Add `sentence` entry to `communication_acts_and_language_entries.md`
   - Define as a group of words that expresses a complete thought
   - Contrast: "A sentence is not a word"

4. Add `idea` / `thought` entry to `logic_entries.md`
   - Define as something that happens in your mind
   - Contrast: "An idea is not a thing you can hold"

### During trunk audit (items 4-11 in todo list)

5. Resolve begin/middle/end ownership (logic vs storytelling)
6. Clarify eat/drink/sleep ownership (STEM vs verbs) as intentional split
7. Clarify sense-verb ownership (STEM vs sensory_experiences) as intentional split
8. Confirm past/present/future ownership lives in time_entries.md

### After trunk audit

9. Verify Tier 3 anchors are clear and early in their files
10. Document any additional gaps discovered during audit

---

## Cross-Reference to Implementation Todo

This ranked gap list supports the following active todo items:

- **Item 3** (this document): Produce a ranked gap list — DONE
- **Items 4-11**: Trunk audit — use Tier 2 ownership resolutions
- **Item 13**: Corpus-wide cleanup pass — use Tier 3 verification list
- **Item 14**: Documentation reconciliation — update dependency_ledger.md with resolutions

---

## Usage Notes

- Use this list when deciding what to fix first during the comprehension pass
- Prefer Tier 1 before Tier 2 before Tier 3
- Do not add Tier 4 concepts unless a specific file requires them
- Update this list if new gaps are discovered during the trunk audit
- Mark items as resolved in this file when completed

---

## Change Log

| Date | Change |
|------|--------|
| 2026-04-17 | Initial ranked gap list created from dependency ledger analysis |
| 2026-04-17 | logic_entries.md audit completed — begin/middle/end split confirmed intentional, own/belong flagged as low-priority overlap |
