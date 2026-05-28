# Corpus Milestone — 2026-05-29

Completed phases from this build cycle. Preserved for reference.

---

## Sequential Training Mode (prerequisite — done)

`train.py` now supports `--no-shuffle` / `--sequential`. Smoke test passed
2026-05-24: sequential batch starts `[0, 4, 8, 12]` on tiny corpus.
Seeded shuffle still available for comparison runs.

---

## Phase A — Grammar Corpus Design

Function-first, case-aware grammar corpus. German dative/accusative as spine;
JP particles as cross-reference cues. Directory structure:

```
training_data/grammar/
  00_relation / 01_means_dative_anchor / 02_receiver_dative /
  03_place_static_dative / 04_change_state / 05_object_accusative_patient /
  06_target_accusative_endpoint / 07_place_target_contrast /
  08_source_path_destination / 09_owner_genitive / 10_review_stories /
  bridge_course
```

Design doc: `docs/grammar_plan.md`. Control files: `training/corpus_admin/grammar/`.

---

## Phase B — Grammar Generation (complete 2026-05-28)

All clusters at 100 files each. Total: 1921 files.

| Cluster | Files |
|---|---:|
| `00_relation` | 4 (relation vocabulary) |
| `01_means_dative_anchor` | 800 (mit/bei/aus/von/zu/nach/seit/gegenüber × 100) |
| `02_receiver_dative` | 16 |
| `03_place_static_dative` | 24 (8 preps × 3) |
| `04_change_state` | 100 |
| `05_object_accusative_patient` | 100 |
| `06_target_accusative_endpoint` | 100 |
| `07_place_target_contrast` | 100 |
| `08_source_path_destination` | 100 |
| `09_owner_genitive` | 100 |
| `10_review_stories` | 100 |
| `bridge_course` | 100 |

Notable fixes during generation: scoped `_zu_`/`_nach_` validators to
`01_means_dative_anchor` only; fixed required_terms for chain files;
added "Do NOT use X" drift guards to prompts.

JP にある/にいる distinction applied throughout static datives.
ZH Traditional Chinese throughout. `wird` + adjective for all change-state files.

---

## Phase C — Grammar Corpus Builder Support (partial, ongoing)

- [x] `build_training_corpus.py` includes `training_data/grammar` in numeric order
- [x] `bridge_design.md` added to exclusion set
- [ ] run-specific corpus output for run_13 (`training/corpus/run13_grammar_ordered.txt`)
- [ ] grammar insertion point confirmed (hypothesis: after `lang_2`, before `lang_3/4`)

---

## Phase F — Wiki Localization (complete 2026-05-29)

2110 EN wiki files (levels 1–4) localised to DE/JP/ZH = 6330 new files.
Done without waiting for wiki split — localized existing level structure.

| Level | EN | DE | JP | ZH |
|---|---:|---:|---:|---:|
| 1 | 1971 | 1971 | 1971 | 1971 |
| 2 | 102 | 102 | 102 | 102 |
| 3 | 19 | 19 | 19 | 19 |
| 4 | 18 | 18 | 18 | 18 |

Script: `meta/scripts/localize_wiki.py`. Naturalness-first prompt with
anti-calque rules for JP (持つ→がある, 着地する→落ちる) and ZH.
Validator fixed for multi-paragraph files (level 2–4).

---

## Phase G — Phase Corpus Localization (complete 2026-05-28)

5806 EN phase files × DE/JP/ZH = 17,418 new files. Prompt uses "localize
naturally" not "translate"; anti-calque guidance; corrected STRUCTURAL_RULES.

---

## Phase G2 — Naturalness Audit and Repair (complete 2026-05-29)

Phase files had ~99% flag rate — generated before 2026-05-28 prompt fix,
full of systematic calques. Fixed with gemma-4-E4B-it locally and
gemma-4-26b-a4b-it via OpenRouter.

| Corpus | Lang | Fixed |
|---|---|---|
| phases | JP | 5292 auto + 3 manual |
| phases | ZH | 3087 auto + 2 accepted + 2 manual |
| grammar | — | 66 lines (CJK terminal punctuation, deterministic) |

Scripts: `audit_localizations.py`, `fix_localizations.py`.
Key fix in `fix_localizations.py`: `_apply_surgical()` guard prevents
unflagged line drift; `_normalize_src()` handles Windows absolute paths
in audit JSONL.

---

## Phase J — Grounded Story Generation (complete 2026-05-29)

195 stories × 4 languages = 780 files total (192 pre-existing + 588 new).

World bible expanded from 5 to 12 locations:
- Pond bench + fish (observation-dependent state)
- Gran's garden (full detail: vegetable patch, henhouse, pear tree, compost, herb trough)
- The upstairs (loft bedroom, skylight, staircase)
- Village lane + village (baker, post box, side street)
- Veterinary surgery (Biscuit, Bello)
- Doctor's surgery
- Sick at Gran's (circumstance entry, not a location)

World topology map added. "No source language" rule: each language
generated independently from spec — no EN reference passed to DE/JP/ZH.
`gen_stories.py` updated: removed EN-first dependency; Bello added to EN
cast; SPATIAL_CONCEPT / TEMPORAL_RELATION / CAUSE_EFFECT /
OBSERVATION_STATE fields parsed and passed as concept constraints.

Story blocks:
- 49–70: new locations and worldbuilding
- 71–90: spatial reasoning (above/below, near/far, through, around, edges)
- 91–110: temporal reasoning (before/after, waiting, transformation, seasons)
- 111–130: cause-effect observation (frost, ice, shadows, sound, evaporation)
- 131–150: two-dog dynamics (Bello learning, cooperation, Biscuit ageing)
- 151–175: extended arithmetic (halving, sharing, measurement, ordinals)
- 176–195: integration (full arcs, familiar scenes revisited)

Future: stories 196+ (object permanence, ripple-uncertainty inference).
See `memory/project_grounded_stories_future.md`.

---

## Corpus state at this milestone

| Layer | Files | Languages |
|---|---:|---|
| phases (1–6) | 5806 × 4 | EN/DE/JP/ZH |
| grammar | 1921 | EN/DE/JP/ZH parallel |
| lang (1–5) | ~18k | EN/DE/JP/ZH |
| wiki (levels 1–4) | 2110 × 4 | EN/DE/JP/ZH |
| triplet_stories | 1345 × 4 | EN/DE/JP/ZH |
| reasoning | ~130 | EN/DE/JP/ZH |
| philosophy | 144 | multilingual tags |
| grounded_stories | 195 × 4 | EN/DE/JP/ZH |
