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

Status: 4 clusters still incomplete. **Finish on Linux.**

Current counts (2026-05-27 end-of-Windows-session):

| Cluster | Files | Remaining |
|---|---:|---:|
| `00_relation` | 88 | 12 |
| `02_receiver_dative` | 99 | 1 |
| `03_place_static_dative` | 100 | — |
| `08_source_path_destination` | 85 | 15 |
| `09_owner_genitive` | 98 | 2 |
| `10_review_stories` | 100 | — |

To finish (skips existing files, safe to re-run):

```bash
for c in 00_relation 02_receiver_dative 08_source_path_destination 09_owner_genitive; do
  python3 meta/scripts/gen_grammar.py --cluster $c --limit 100 >> /tmp/${c}_gen.log 2>&1 &
done
```

**Resume here (Linux):** Run the above, wait for completion, then spot-audit 2-3 files per cluster (German case, JP plain form, ZH Traditional), then proceed to Phase G below. Run this to check phase localization progress:

```bash
for c in 00_relation 02_receiver_dative 03_place_static_dative 08_source_path_destination 09_owner_genitive 10_review_stories; do
  echo "$c: $(ls training_data/grammar/$c/ | wc -l)/100"
done
```

If any cluster is below 100, re-run its generator (it skips existing files):

```bash
python3 meta/scripts/gen_grammar.py --cluster 08_source_path_destination
```

After all clusters reach 100: do a spot audit of each new cluster (read 2-3 files, check German case, JP plain form, ZH Traditional), then proceed to **Phase G** (phase localization).

Note: `10_review_stories` reached 100 on 2026-05-27 night. All 4 previously-failing `zwischen`/demonstrative files were force-regenerated successfully.

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

Status: IN PROGRESS. Windows session 2026-05-27 started 3 nohup processes (one per language).
Processes may still be running when Linux session begins — check before launching new ones.

End-of-Windows-session counts (2026-05-27 ~18:xx local):

| Lang | Done | Remaining | Errors (missed files) |
|---|---:|---:|---|
| DE | 5126 | 680 | 0 |
| JP | 1775 | 4031 | 10 (road_2→room) |
| ZH | 2079 | 3727 | 10 (dot→driftwood) |

Missed-error files will be picked up automatically on restart (they were never written).

**Script:** `meta/scripts/localize_phases.py`

**Resume here (Linux):**

```bash
# Step 1 — check if Windows processes are still running
ps aux | grep localize_phases | grep -v grep

# Step 2 — check current progress
PYTHONIOENCODING=utf-8 python3 meta/scripts/localize_phases.py report

# Step 3 — for any language not yet at 5806, restart its process (skips existing files):
OPENROUTER_API_KEY=<key> nohup python3 meta/scripts/localize_phases.py gen \
  --phase all --lang DE --workers 1 --batch 10 >> tmp/localize_DE.log 2>&1 &
OPENROUTER_API_KEY=<key> nohup python3 meta/scripts/localize_phases.py gen \
  --phase all --lang JP --workers 1 --batch 10 >> tmp/localize_JP.log 2>&1 &
OPENROUTER_API_KEY=<key> nohup python3 meta/scripts/localize_phases.py gen \
  --phase all --lang ZH --workers 1 --batch 10 >> tmp/localize_ZH.log 2>&1 &
```

**Bidirectional speedup for JP/ZH (when DE is done):**
JP and ZH are slow (~6 files/min). To finish faster, run 2 processes per language:
one forward (default) + one reverse (needs `--reverse` flag — not yet implemented, add it).
4 processes total: JP-forward, JP-reverse, ZH-forward, ZH-reverse, meeting in the middle.
This roughly halves remaining time for JP/ZH.

Produces `_DE.md`, `_JP.md`, `_ZH.md` siblings for every English phase file. Skips already-done files; safe to re-run after interruption. Validates `[user]`/`[Ninereeds]` structure and ZH/JP character presence on every output before writing.

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

Full localization adds ~17,418 files (5,806 × 3 languages). The `_2` duplicate files (380 total across all phases) are included — localize them all.

Output naming:

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
