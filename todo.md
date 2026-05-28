# TODO

Active work queue. See `docs/training.md` for the full procedure.

---

## Current Direction

Corpus is in good shape. Localisation and audit backlog is clear.
Active tasks in priority order:

1. **Phase J** — Grounded story generation (running now, 49–195 × 4 langs)
2. **Phase D** — Run 13: grammar-ordered corpus, sequential training
3. **Phase I** — Adversarial corpus critic (before run 13 if time allows)
4. **Phase E/H** — Wiki split + ordering manifests (lower urgency now that
   wiki is localized)

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

Status: **COMPLETE 2026-05-28.** All clusters at 100 files. Committed and pushed.

| Cluster | Files | Status |
|---|---:|---|
| `00_relation` | 100 | done |
| `01_means_dative_anchor` | 800 | done |
| `02_receiver_dative` | 100 | done |
| `03_place_static_dative` | 100 | done |
| `04_change_state` | 100 | done |
| `05_object_accusative_patient` | 100 | done |
| `06_target_accusative_endpoint` | 100 | done |
| `07_place_target_contrast` | 100 | done |
| `08_source_path_destination` | 100 | done |
| `09_owner_genitive` | 100 | done |
| `10_review_stories` | 100 | done |
| `bridge_course` | 100 | done |

Also fixed several spec/validator bugs in `gen_grammar.py` during this session:
- Scoped `_zu_` and `_nach_` audit validators to `01_means_dative_anchor` only (were
  incorrectly firing on `08_source_path_destination` chain/review files).
- Fixed required_terms for chain files to use full dative forms, not contractions.
- Added explicit "Do NOT use X" guards to prompts that kept drifting.

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

### Completed: `04_change_state` — 100 files

Status: complete 2026-05-26. 100/100 generated. Corpus dry-run pass: clean.

Original 12: temperature (kalt/warm/heiß/kühl), physical (hart/weich/nass/trocken), living (müde/wach/krank/gesund). Expanded to 100 with: voll/leer/sauber/schmutzig/kaputt/hell/dunkel/laut/leise/schwer/leicht/offen/geschlossen/frisch/eisig/glatt/rau/süß/hungrig/durstig/satt/stark/schwach/ruhig/still/glücklich/traurig/froh/böse/wütend/nervös/aufgeregt/stolz/blass/fertig/bereit/aktiv/groß/alt/rot + second-wave _b/_c variants. `wird` + adjective throughout. JP 〜くなる / 〜になる. ZH 變〜了.

### Completed: `05_object_accusative_patient` — 100 files

Status: 100 files complete 2026-05-26. 100/100 generated; 1 validation failure on first pass, passed on retry. Corpus dry-run pass: clean.

16 original verbs + 24 new verbs (trinken/schließen/holen/kochen/backen/heben/putzen/reparieren/suchen/verlieren/schlagen/hören/fangen/streicheln/kennen/beobachten/packen/füllen/pflücken/wiegen/bauen/schieben/messen/wischen/schütteln/drücken/rollen/falten/wählen). Gender contrast (den/die/das) throughout. JP を throughout. ZH SVO Traditional.

### Completed: `06_target_accusative_endpoint` — 100 files

Status: complete 2026-05-27. 100/100 generated. Corpus dry-run pass: 1245/1245 grammar files included.

8 two-way prepositions × 12-13 files each: auf/in/über/unter/neben/vor/hinter/zwischen, all in accusative (movement endpoint). Agent movement + object placement verbs (gehen/laufen/legen/stellen/setzen/hängen/bringen/kriechen). Gender contrast files included per preposition. Drift guards: requires accusative two-way prep, bans dative forms, requires movement/placement verb. JP の上に/下に/前に/後ろに/隣に/間に + verb. ZH Traditional 放到/走到/帶到.

### Completed: `07_place_target_contrast` — 100 files

Status: complete 2026-05-27. 100/100 generated. Corpus dry-run pass: 1345/1345 grammar files included.

8 two-way prepositions × 12-13 files each: auf/in/über/unter/neben/vor/hinter/zwischen. Each file alternates static dative pairs (auf dem/in der etc. + ist/liegt/steht/hängt) and endpoint accusative pairs (auf den/in die etc. + stellt/legt/geht/bringt). Four drift guards: requires dative two-way prep, requires accusative two-way prep, requires static verb, requires movement/placement verb. JP にある vs に置く distinction. ZH 在〜 vs 放到〜 contrast. Traditional Chinese throughout.

### Next: `08_source_path_destination` — 100 files

Plan: source/path/destination chains. Core German: `aus der Küche in den Garten`, `von meinem Haus zum Kino`, `vom Baum zur Bank`. JP from/to particles: から, まで, へ, に. Cluster should only appear after 07 contrast is established. Generate spec function in `gen_grammar.py` then generate in a single batch.

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
| `06_target_accusative_endpoint` | 100 | movement endpoint |
| `07_place_target_contrast` | 100 | static vs endpoint contrast |
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

Status: **COMPLETE 2026-05-29.**

Localized the wiki in its existing level structure (levels 1–4) rather than
waiting for the split. 2110 EN source files × DE/JP/ZH = 6330 new files.

| Level | EN files | DE | JP | ZH |
|---|---:|---:|---:|---:|
| 1 | 1971 | 1971 | 1971 | 1971 |
| 2 | 102 | 102 | 102 | 102 |
| 3 | 19 | 19 | 19 | 19 |
| 4 | 18 | 18 | 18 | 18 |

Script: `meta/scripts/localize_wiki.py`
Naturalness-first prompt with anti-calque rules for JP/ZH.
Phase E (wiki split) remains useful for curriculum ordering but is no longer
a prerequisite for multilingual training.

---

## Phase G — Phase Corpus Localization

Status: **COMPLETE 2026-05-28.** All 5806 × 3 languages done.

| Lang | Done | Status |
|---|---:|---|
| DE | 5806/5806 | done |
| JP | 5806/5806 | done |
| ZH | 5806/5806 | done |

Prompt fix applied during this session: `localize_phases.py` uses "localize naturally" (not
"translate"), anti-calque guidance with JP/ZH examples, corrected `STRUCTURAL_RULES` (removed
hardcoded "6 lines", clarified 1-to-1 line mapping).

---

## Phase G2 — Naturalness Audit and Repair

Status: **COMPLETE 2026-05-29.**

| Corpus | Lang | Files | Fixed | Notes |
|---|---|---|---|---|
| phases | JP | 5806/5806 | 5292 auto + 3 manual | done |
| phases | ZH | 5806/5806 | 3087 auto + 2 accepted + 2 manual | done |
| grammar | — | 66 lines | deterministic | CJK terminal punctuation |

Scripts: `meta/scripts/audit_localizations.py`, `fix_localizations.py`
Audit logs: `tmp/audit_JP_phases.jsonl`, `tmp/audit_ZH_phases.jsonl`

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

## Phase I — Adversarial Corpus Critic

Status: **planned** (high-priority after Phase G2 audit/fix pass).

Rationale: the corpus is the only lever on a small model. A single malformed file
has outsized impact. The current audit/fix pipeline catches naturalness issues, but
the broader threat is larger: schema breaks, pronoun leakage, Simplified Chinese,
wrong register, vocabulary outside the allowlist, hallucinated facts, etc.

Design: a full adversarial critic that *assumes the corpus is guilty* and finds
every place it could poison a tiny model. The critic does NOT fix anything — it
produces a triage map only.

### Triage verdict levels

| Verdict | Meaning |
|---|---|
| `PASS` | No issues found |
| `PATCH` | Fixable by deterministic script (e.g. strip extra line, wrong tag casing) |
| `REGENERATE` | File needs full regeneration — broken structure or wrong content |
| `HUMAN_REVIEW` | Ambiguous; human must decide |

### Reason tags

```
[STRUCT]          [user]/[Ninereeds] count wrong, tag format broken, wrong line count
[POS]             Part-of-speech misuse, wrong register, pronoun leaked
[SEMANTIC_DRIFT]  Meaning has drifted from expected concept definition
[JP_NATURALNESS]  Calque verb, wrong counter, unnatural expression
[ZH_SIMPLIFIED]   Simplified Chinese characters found
[ZH_NATURALNESS]  Calque expression, unnatural phrasing
[DE_CASE]         Wrong dative/accusative case form
[ALLOWLIST]       Vocabulary outside inventory/allowlist.txt
[ABSTRACTION]     Metaphor too abstract for a small model's concept stage
[NEGATION]        Negation in body lines
[DUPLICATE]       Duplicate or conflicting concept definition
[HALLUCINATION]   Factual claim that is wrong or unverifiable
```

### Architecture

Three-tier pipeline:

1. **Deterministic pre-screen** (Python, no API call) — catches `[STRUCT]`, `[ZH_SIMPLIFIED]`,
   `[NEGATION]`, `[ALLOWLIST]` without spending tokens. Emits `PATCH` or `PASS` verdicts
   directly. Only unknowns go to tier 2.

2. **LLM critic** (DeepSeek, batch) — reviews each file with EN context. Produces
   `REGENERATE` or `HUMAN_REVIEW` verdicts with reason tags. Cheap models work here
   because the task is detection, not generation.

3. **Fix dispatcher** — routes `PATCH` verdicts to deterministic scripts (strip_opener.py,
   tag normalizers, etc.), `REGENERATE` verdicts to the appropriate generator, and
   `HUMAN_REVIEW` verdicts to a human-readable triage queue.

### Output

```
tmp/critic_triage.jsonl       — one record per file: {file, verdict, tags, detail}
tmp/critic_patch_queue.txt    — files needing deterministic patch
tmp/critic_regen_queue.txt    — files needing regeneration
tmp/critic_human_queue.txt    — files needing human review
```

### Coverage

Apply to all corpus layers in priority order:
1. `training_data/phases/` (phase_1–6, all languages) — highest training weight
2. `training_data/grammar/` (new; grammar errors poison case learning)
3. `training_data/lang/` (lang_1–5)
4. `training_data/triplet_stories/` (naturalness + vocabulary)
5. `training_data/reasoning/`, `training_data/philosophy/` (lower priority)

Implementation: `meta/scripts/corpus_critic.py`

---

## Phase J — Grounded Story Generation (49–195)

Status: **RUNNING 2026-05-29.**

World bible and storylist expanded during this session:
- Cast: Emma, Taro, Gran, Biscuit, Bello
- Locations: 5 → 12 (added pond bench, garden detail, upstairs, village
  lane, village, vet, doctor's surgery, sick-at-Gran's)
- World topology map added to world bible
- "No source language" rule: each language written independently from spec
- Storylist: 48 → 195 stories (blocks: new locations, spatial reasoning,
  temporal reasoning, cause-effect, two-dog dynamics, extended arithmetic,
  integration)

New metadata fields in storylist: `SPATIAL_CONCEPT`, `TEMPORAL_RELATION`,
`CAUSE_EFFECT`, `OBSERVATION_STATE` — concept constraints passed to model.

Files: `training/corpus_admin/grounded_stories/world_bible.md`, `storylist.txt`
Script: `meta/scripts/gen_stories.py`

Generation: 588 jobs (stories 49–195 × EN/DE/JP/ZH), workers=6.

```bash
KEY=$(grep OPENROUTER_API_KEY .env | cut -d= -f2-)
OPENROUTER_API_KEY="$KEY" nohup python3 -B meta/scripts/gen_stories.py gen \
  --lang EN,DE,JP,ZH --workers 6 >> tmp/gen_stories.log 2>&1 &
```

Report:

```bash
python3 -B meta/scripts/gen_stories.py report
```

Stories 196+ (future, not started): object permanence arc, ripple-uncertainty
arc. See `memory/project_grounded_stories_future.md`.

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
