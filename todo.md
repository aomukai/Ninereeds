# TODO

Active work queue. See `docs/training.md` for the full procedure.

---

## Current Direction

The next work is curriculum expansion and ordering, not another immediate
training run.

Core shift:

- move from topic-first ordering toward function-first curriculum design
- preserve deterministic training order instead of shuffling windows
- add a dedicated multilingual grammar corpus
- prepare wiki and phase corpora for finer-grained sequencing and multilingual
  concept anchoring

Primary design reference:

- `docs/grammar_plan.md`

Primary new corpus root:

- `training_data/grammar/`

---

## Non-Negotiable Training Requirement

Before launching any grammar or ordered-curriculum run, `train.py` must support
a sequential/no-shuffle mode.

Current state:

- `train.py` uses `torch.randperm` in `make_batches`
- seeding makes the shuffle repeatable
- repeatable shuffle is not sufficient for this curriculum
- the intervention requires Ninereeds to see content in the exact order emitted
  by the corpus builder

Required implementation:

- [x] add a CLI flag such as `--no-shuffle` or `--sequential`
- [x] when enabled, consume byte windows in corpus order
- [x] keep seeded shuffle available for old comparisons
- [x] record shuffle mode in training logs
- [x] update docs before any run uses the new mode

No-shuffle smoke test: passed on 2026-05-24 with project Python and a tiny byte
corpus; sequential batch starts were `[0, 4, 8, 12]`.

---

## Phase A — Grammar Corpus Design

Status: in progress.

Directory structure:

```text
training_data/grammar/
  00_relation/
  01_means_dative_anchor/
  02_receiver_dative/
  03_place_static_dative/
  04_change_state/
  05_object_accusative_patient/
  06_target_accusative_endpoint/
  07_place_target_contrast/
  08_source_path_destination/
  09_owner_genitive/
  10_review_stories/
```

Design principle:

- function-first, case-aware
- German dative/accusative is the spine
- Japanese particles are cross-reference cues, not one-to-one equivalents
- topics are example domains, not the ordering principle

Open tasks:

- [x] Fill `training_data/grammar/manifest.md`
- [x] Define file counts per grammar directory
- [x] Define naming convention for files inside each directory
- [ ] Define allowed names, objects, verbs, and places for the grammar corpus
- [x] Write DeepSeek generation prompt for `00_relation`
- [ ] Write validation checklist as an executable script or documented manual gate

Initial generation order:

1. `00_relation` — generated and structurally validated
2. `01_means_dative_anchor`
3. `02_receiver_dative`
4. `03_place_static_dative`
5. `04_change_state`
6. `05_object_accusative_patient`
7. `06_target_accusative_endpoint`
8. `07_place_target_contrast`
9. `08_source_path_destination`
10. `09_owner_genitive`
11. `10_review_stories`

Grammar corpus constraints:

- short `[user]` / `[Ninereeds]` files
- 4-8 pairs per file
- responses include EN, DE, JP, ZH parallel lines
- German case form must match the cluster target
- JP must use plain form and no romaji
- ZH must use Traditional Chinese
- no long grammar lectures except in explicit contrast files

---

## Phase B — Grammar Generation

Status: `01_means_dative_anchor`, `02_receiver_dative`, `bridge_course`, `03_place_static_dative` complete. Active work is now `04_change_state`.

**Resume here next session: `04_change_state`.** Read `claude.md` and this file — no other handoff doc is needed.

### Completed: `01_means_dative_anchor` — 800 files, all 8 prepositions at 100 each

| Preposition | Files | Range | Status |
|---|---|---|---|
| `mit` | 100 | 001–100 | done |
| `bei` | 100 | 101–200 | done |
| `aus` | 100 | 201–300 | done |
| `von` | 100 | 301–400 | done |
| `zu` | 100 | 401–500 | done |
| `nach` | 100 | 501–600 | done |
| `seit` | 100 | 601–700 | done |
| `gegenüber` | 100 | 701–800 | done |

### Completed: `02_receiver_dative` — 16 files, all 8 verbs

Status: complete 2026-05-26. Spot audit clean. Full corpus dry-run pass.

### Completed: `bridge_course` — 100 files

Status: complete 2026-05-26. All 3 groups generated and validated. Corpus builder updated with bridge dispatcher. Corpus dry-run pass: 921/921 grammar files included.

Groups: A (001–050) ditransitive Wer/Wem/Was, B (051–070) ditransitive+genitive Wer/Wem/Was/Wessen, C (071–100) pure-dative Wer/Wem.

### Completed: `03_place_static_dative` — 24 files

Status: complete 2026-05-26. 24/24 generated clean on first pass. Spot audit clean. Corpus dry-run pass: 945/945 grammar files included.

8 two-way prepositions × 3 files each: auf/in/über/unter/neben/vor/hinter/zwischen, all in dative. Static location only. Drift guards added to validator (accusative forms, movement verbs, missing dative prep). JP にある/にいる distinction applied correctly.

### Active cluster: `04_change_state`

Status: specs not yet written. This is the first task for the next session.

Target: 12 files. Purpose: becoming / state-change patterns (`werden` + predicate).

Core German patterns to cover:

- `Das Wasser wird kalt.`
- `Das Brot wird hart.`
- `Das Kind wird müde.`
- `Die Suppe wird warm.`

Requirements:
- Focus on `werden` as the change-of-state copula, not movement.
- Adjective predicate changes across the 4 pairs (cold→hot, hard→soft, tired→awake, etc.).
- JP cross-cue: `〜になる` pattern.
- ZH cross-cue: `變得〜` pattern.
- 4 pairs per file, EN/DE/JP/ZH format.

**Steps to start:**

1. Add `make_change_state_specs()` to `meta/scripts/gen_grammar.py`.
2. Add `04_change_state` drift guards to the validator (no movement verbs, werden must appear).
3. Add cluster key to `CLUSTERS`.
4. Dry-run, audit batch of 6, corpus check, then remaining 6 files.
5. Update manifest and this file when done.

Generation command pattern:
```bash
python3 meta/scripts/gen_grammar.py --cluster 01_means_dative_anchor_nach_audit --limit 10
python3 meta/scripts/gen_grammar.py --cluster 01_means_dative_anchor_nach_audit --offset 10 --limit 15
```

Regenerate a failed file (never written on FAIL):
```bash
python3 meta/scripts/gen_grammar.py --cluster 01_means_dative_anchor_nach_audit --match "NNN"
```

Corpus validation after each batch:
```bash
python3 meta/scripts/build_training_corpus.py --dry-run
```

### Remaining always-dative anchors after `nach`

From `training_data/grammar/prepositions.md` Tier 2:

| Preposition | Notes |
|---|---|
| `seit` | since / for — temporal; leave until after spatial anchors complete |
| `gegenüber` | opposite — static spatial; leave until after spatial anchors complete |

Generate with DeepSeek one directory at a time.

Do not generate the entire grammar corpus in one bulk request.

Per-directory workflow:

1. Prepare exact prompt.
2. Generate files.
3. Validate structure.
4. Audit a sample manually.
5. Record completion in `training_data/grammar/manifest.md`.
6. Only then proceed to the next directory.

Target count from `docs/grammar_plan.md`:

| Directory | Approx files | Purpose |
|---|---:|---|
| `00_relation` | 4 | relation vocabulary — done |
| `01_means_dative_anchor` | 500+ | always-dative anchors — in progress |
| `02_receiver_dative` | 16 | recipient / indirect object |
| `03_place_static_dative` | 24 | static spatial dative |
| `04_change_state` | 12 | becoming / state change |
| `05_object_accusative_patient` | 16 | direct object |
| `06_target_accusative_endpoint` | 24 | movement endpoint |
| `07_place_target_contrast` | 18 | static vs endpoint contrast |
| `08_source_path_destination` | 16 | source/path/destination chains |
| `09_owner_genitive` | 8 | ownership / attribute |
| `10_review_stories` | 12 | grounded reinforcement |

Important early examples:

- prefer visibly marked dative receivers such as `dem Jungen`, `dem Mann`,
  `dem Arzt`, `der Frau`, `dem Kind`
- avoid early bare-name receiver examples such as `Emma gibt Taro den Apfel`
- split `mit` internally into accompaniment, instrument, and vehicle/means:
  `mit dem Hund`, `mit dem Hammer`, `mit dem Bus`

---

## Phase C — Grammar Corpus Builder Support

Status: in progress.

Required changes:

- [x] update `meta/scripts/build_training_corpus.py` to include `training_data/grammar`
- [x] preserve numeric directory order
- preserve manifest order if `training_data/grammar/manifest.md` is present
- validate grammar files separately from phase/wiki files if needed
- [ ] add a run-specific output for grammar experiments, e.g.
  `training/corpus/run13_grammar_ordered.txt`

Question to resolve:

- Should grammar be inserted before `lang_3/lang_4`, after them, or immediately
  before reasoning?

Current hypothesis:

- insert grammar after `lang_2` and before advanced `lang_3/lang_4` exposure for
  a clean function-first scaffold
- run_13 can test this explicitly

---

## Phase D — Run 13

Status: blocked by Phase A-C and sequential training mode.

Goal:

- test whether grammar-function ordering improves German dative/accusative
  behavior, spatial relation output, and general routing at 150M

Run shape:

- model: `--scale-150m`
- corpus: ordered full corpus with grammar inserted
- training mode: sequential/no-shuffle
- epochs: 3 unless `docs/training.md` is updated with a different decision
- base: scratch unless an architecturally compatible 150M checkpoint is selected

Primary probes:

- `Die Wolke ist über dem Berg.`
- `Das Kind geht in den Garten.`
- `Emma gibt dem Jungen den Apfel.`
- `Der Becher ist auf dem Tisch.`
- `Emma stellt den Becher auf den Tisch.`

Secondary checks:

- JP location uses plausible `にある` / location phrasing
- JP object use includes `を` where appropriate
- spatial relation output improves in EN/DE
- arithmetic echo pressure does not worsen
- shaped score and loop count remain promotion gates

Deliverables:

- [ ] `training/corpus/run13_grammar_ordered.txt`
- [ ] `training/corpus/run13_build_report.txt`
- [ ] `training/logs/run_13_report.md`
- [ ] per-epoch probe + eval results

---

## Phase E — Wiki Splitting

Status: planned.

Rationale:

- wiki is currently the largest English-only concept-definition layer
- many wiki files contain many unrelated `[user]` blocks
- ordering is too coarse for a deterministic curriculum

Observed current shape:

- `training_data/wiki/` has 152 markdown files
- 138 files contain more than one `[user]` block
- those multi-entry files contain 2,355 `[user]` blocks
- largest observed wiki file has 107 `[user]` blocks

Plan:

- create a split mirror first, not an in-place destructive rewrite
- use subfolders freely
- preserve current wiki as source until validation passes

Proposed target:

```text
training_data/wiki_split/
  wiki_1/
    STEM/
      hot/
        EN.md
      cold/
        EN.md
  wiki_2/
    health_and_wellness/
      fever/
        EN.md
```

Splitting rule:

- Level 1: split mostly one `[user]` block per concept file
- Level 2-4: split by nearest meaningful heading or subsection when prompts
  depend on local context
- do not orphan follow-up prompts such as `Does it need to be washed?`

Validation:

- same total `[user]` count as source
- same total `[Ninereeds]` count as source
- no empty prompt/response files
- no lost headings where heading context is required
- generate a manifest for wiki ordering before adding to corpus builder

---

## Phase F — Wiki Localization

Status: planned after wiki split.

Rationale:

- current wiki is English-only
- lang/reasoning/stories/philosophy are already multilingual
- English-only wiki biases concept definitions toward English retrieval

Plan:

- localize split wiki units selectively, not all at once
- start with concepts relevant to grammar, spatial relations, actions, source,
  target, ownership, and change
- keep English concept slug as folder name

Preferred structure:

```text
training_data/wiki_split/wiki_1/STEM/hot/
  EN.md
  DE.md
  JP.md
  ZH.md
```

Localization constraints:

- DE: clear Schulbuch style
- JP: plain form, no romaji
- ZH: Traditional Chinese
- preserve concept meaning, not literal English syntax
- avoid adding new facts unless needed for natural localization

This is not part of run_13 unless explicitly scoped later.

---

## Phase G — Phase Corpus Localization

Status: planned as a separate major expansion.

Rationale:

- phases 1-6 are the primary concept-definition layer
- phases are currently English-only
- multilingual phase variants would anchor early concepts directly in DE/JP/ZH

Current phase size:

| Phase | EN files |
|---|---:|
| phase_1 | 1,450 |
| phase_2 | 740 |
| phase_3 | 1,387 |
| phase_4 | 261 |
| phase_5 | 376 |
| phase_6 | 1,592 |
| total | 5,806 |

Full localization would add about 17,418 files.

Preferred naming:

```text
training_data/phases/phase_1/apple.md
training_data/phases/phase_1/apple_DE.md
training_data/phases/phase_1/apple_JP.md
training_data/phases/phase_1/apple_ZH.md
```

Rules:

- keep English slug as file stem
- preserve `[user]` / `[Ninereeds]` structure
- preserve number of pairs
- preserve the teaching rhythm
- do not add uncontrolled vocabulary
- localize naturally, not word-for-word

Pilot candidates:

- phase_6 bridge words: `question`, `answer`, `word`, `sentence`, `plan`,
  `goal`, `true`, `real`
- phase_1 concrete nouns needed by grammar: `apple`, `boy`, `girl`, `man`,
  `woman`, `doctor`, `teacher`, `table`, `bench`, `kitchen`, `garden`, `bus`,
  `hammer`, `ball`

Do not generate all phase localizations before a pilot is validated.

---

## Phase H — Ordering Manifests

Status: planned.

Manifests should be human-readable markdown first. JSON can be generated later
if tooling needs it.

Required manifests:

- `training_data/grammar/manifest.md`
- `training_data/wiki_split/manifest.md`
- optional: `training_data/phases/phase_manifest.md`

Manifest responsibilities:

- define explicit corpus order
- identify source files
- identify generated language variants
- record validation status
- record generation/audit batches

The corpus builder should prefer manifest order over filesystem order when a
manifest exists.

---

## Stop Gates

Pause before training if any of these are true:

- sequential/no-shuffle mode is not implemented
- grammar manifest is empty or incomplete
- grammar files have unvalidated language/case forms
- corpus builder skips any files
- wiki split loses or duplicates `[user]` / `[Ninereeds]` blocks
- phase localization pilot changes structure or adds uncontrolled vocabulary

Pause after training if any of these are true:

- loops >= 4
- abrupt stops >= 2
- shaped score collapses relative to comparable baseline
- grammar probes improve but general shaped score fails promotion gates
