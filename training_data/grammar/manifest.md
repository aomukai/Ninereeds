# Grammar Curriculum Manifest

Purpose: define the intended generation and training order for
`training_data/grammar/`.

This manifest is the human-readable source of truth. Tooling may later derive
JSON from it, but corpus building should preserve this order.

Design reference: `docs/grammar_plan.md`

---

## Status

| Stage | Status |
|---|---|
| Directory structure | complete |
| File naming convention | draft |
| Generation prompts | in progress |
| Generated files | `00_relation` complete; `mit` `bei` `aus` `von` `zu` `nach` `seit` `gegenüber` — 100 files each, all generated and audited |
| Validation scripts | in progress |
| Corpus-builder integration | complete |

---

## File Convention

Use numeric prefixes inside each directory so local file order is stable.

Recommended pattern:

```text
NN_short_slug.md
```

Examples:

```text
01_means_dative_anchor/001_mit_accompaniment.md
01_means_dative_anchor/002_mit_instrument.md
01_means_dative_anchor/003_mit_vehicle.md
02_receiver_dative/001_give_dem_jungen.md
```

Each file should contain 4-8 `[user]` / `[Ninereeds]` pairs. Each response should
contain parallel EN, DE, JP, and ZH lines unless a cluster prompt explicitly says
otherwise.

---

## Allowed Core Cast

Prefer these names and roles for continuity:

- Emma
- Taro
- Gran
- Biscuit
- the boy
- the girl
- the woman
- the man
- the doctor
- the teacher

For early German dative receiver files, prefer visibly marked noun phrases:

- `dem Jungen`
- `dem Mann`
- `dem Arzt`
- `dem Lehrer`
- `der Frau`
- `dem Kind`
- `dem Hund`

Avoid bare proper-name receivers in early dative files, e.g.
`Emma gibt Taro den Apfel`, because the receiver is not visibly marked.

---

## Ordered Clusters

### 00_relation

Status: generated and structurally validated.

Purpose: bridge vocabulary for grammar functions.

Target files: 4

Concepts:

- relation
- receiver
- place
- source
- target
- path
- owner
- object
- action
- change
- means

Validation focus:

- simple explanations only
- no heavy grammar lecture
- no uncontrolled abstract vocabulary

### 01_means_dative_anchor

Status: all 8 prepositions at 100 files each (800 files total) — **complete.** File ranges: `mit` 001–100, `bei` 101–200, `aus` 201–300, `von` 301–400, `zu` 401–500, `nach` 501–600, `seit` 601–700, `gegenüber` 701–800.

Purpose: build the German dative retrieval pathway with always-dative
prepositions before ambiguous two-way prepositions.

Target files: at least 100 per preposition for full preposition drills; this cluster starts with `mit`.

Subclusters:

- `mit` accompaniment: `mit dem Hund`
- `mit` instrument: `mit dem Hammer`
- `mit` vehicle/means: `mit dem Bus`
- `bei`: `bei dem Baum`, `bei der Schule`, `bei dem Haus`
- `von`: `von dem Tisch`, `von der Bank`, `von dem Fenster`
- `aus`: `aus dem Garten`, `aus der Küche`, `aus dem Zimmer`
- `zu`: `zu dem Kind`, `zu der Tür`, `zu dem Tor`
- `nach`, `seit`, `gegenüber`

Japanese cross-cues:

- `と` for accompaniment
- `で` for instrument, means, and vehicle
- `に` for destination/person relation
- `から` for source

Validation focus:

- German noun phrase must be dative
- do not introduce two-way static/movement contrast yet

### 02_receiver_dative

Status: generated and validated — 16 files complete.

Purpose: recipient, beneficiary, and indirect-object patterns.

Target files: 16

Core German patterns:

- `dem Kind geben`
- `der Frau zeigen`
- `dem Hund helfen`
- `dem Lehrer antworten`
- `Emma gibt dem Jungen den Apfel`
- `Taro zeigt dem Mann das Buch`
- `Gran hilft dem Arzt`

Japanese cross-cue:

- `に`

Validation focus:

- receiver dative must be visibly marked
- accusative object may appear, but the file target remains the receiver
- do not use bare proper-name receivers in early files

### 03_place_static_dative

Status: not generated.

Purpose: static location and spatial relation.

Target files: 24

Core German patterns:

- `auf dem Tisch`
- `in der Küche`
- `über dem Berg`
- `unter der Bank`
- `neben dem Baum`
- `vor dem Haus`
- `hinter der Tür`
- `zwischen den Stühlen`

Japanese cross-cues:

- `にある`
- `で` for activity location
- `の上に`, `の下に`, `の前に`, `の後ろに`, `の隣に`

Validation focus:

- no movement endpoint examples
- German static two-way prepositions use dative
- this cluster should also strengthen spatial reasoning

### 04_change_state

Status: not generated.

Purpose: becoming, waking, growing, and state transition.

Target files: 12

Core patterns:

- `Der Baum wird größer.`
- `Taro wacht auf.`
- `Das Wasser wird warm.`
- `Der Teig wird Brot.`

Japanese cross-cues:

- `になる`
- `くなる`
- `起きる`

Validation focus:

- keep distinct from endpoint movement
- keep examples concrete

### 05_object_accusative_patient

Status: not generated.

Purpose: direct object / acted-on patient.

Target files: 16

Core German patterns:

- `Emma sieht den Hund.`
- `Taro trägt den Korb.`
- `Gran schneidet den Apfel.`
- `Emma öffnet die Tür.`
- `Taro nimmt das Buch.`

Japanese cross-cue:

- `を`

Validation focus:

- plain transitive action
- do not mix with dative receiver yet

### 06_target_accusative_endpoint

Status: not generated.

Purpose: movement endpoint with two-way prepositions.

Target files: 24

Core German patterns:

- `in die Küche`
- `auf den Tisch`
- `unter die Bank`
- `an die Tür`
- `hinter den Stuhl`

Japanese cross-cues:

- `に`
- `へ`
- endpoint phrasing such as `の上に置く`

Validation focus:

- movement endpoint uses accusative
- do not mix with source/path chains yet

### 07_place_target_contrast

Status: not generated.

Purpose: explicit contrast between static place and movement endpoint.

Target files: 18

Contrast pairs:

- `Der Becher ist auf dem Tisch.`
- `Emma stellt den Becher auf den Tisch.`
- `Der Hund ist unter der Bank.`
- `Der Hund läuft unter die Bank.`
- `Taro ist in der Küche.`
- `Taro geht in die Küche.`

Validation focus:

- paired examples should share nouns and prepositions
- German case contrast must be visible

### 08_source_path_destination

Status: not generated.

Purpose: mixed source, path, and destination chains.

Target files: 16

Core German patterns:

- `von meinem Haus zum Kino`
- `aus der Küche in den Garten`
- `vom Baum zur Bank`
- `aus dem Haus und unter den Tisch`

Japanese cross-cues:

- `から`
- `まで`
- `へ`
- `に`

Validation focus:

- comes only after static/endpoint contrast
- mixed cases are acceptable here because the scaffold is already established

### 09_owner_genitive

Status: not generated.

Purpose: ownership and attribute relation.

Target files: 8

Core patterns:

- `Emmas Becher`
- `der Becher von Emma`
- `die Farbe des Blattes`
- `die Tür des Hauses`

Japanese cross-cue:

- `の`

Validation focus:

- keep light and late
- `von` possession is acceptable alongside formal genitive

### 10_review_stories

Status: not generated.

Purpose: grounded reinforcement after exact retrieval is established.

Target files: 12

Story pattern:

- short concrete event
- repeated relation patterns
- no new grammar target introduced

Example arc:

- Emma gives the boy an apple.
- Taro puts the apple on the table.
- The apple is on the table.
- Biscuit runs under the bench.
- Gran takes the apple from the table.

Validation focus:

- story reinforces earlier clusters
- narrative should not replace exact pattern training

---

## Completion Ledger

Add one line per generated/audited batch:

| Date | Cluster | Files | Generator | Validation | Notes |
|---|---|---:|---|---|---|
| 2026-05-24 | `00_relation` | 4 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | tag counts + full corpus dry-run pass | Minor manual cleanup for tag spacing, name preservation, and pronoun removal. |
| 2026-05-24 | `01_means_dative_anchor` / `mit` | 25 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | tag counts + targeted `mit` drift scan + full corpus dry-run pass | First continuation batch exposed off-lexicon instrument targets and Simplified Chinese; generator validation was tightened before accepting the batch. |
| 2026-05-24 | `01_means_dative_anchor` / `mit` | 40 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `mit` drift scan + spot audit + full corpus dry-run pass | Second continuation batch exposed demonstratives and wagon/horse-carriage drift; generator validation was tightened before accepting the batch. |
| 2026-05-24 | `01_means_dative_anchor` / `mit` | 55 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `mit` drift scan + spot audit + full corpus dry-run pass | Third continuation batch had one vehicle/animal validation failure for `049`; clean retry was accepted. |
| 2026-05-24 | `01_means_dative_anchor` / `mit` | 70 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `mit` drift scan + spot audit + full corpus dry-run pass | Fourth continuation batch had one vehicle/animal validation failure for `061`; `063` ball examples were regenerated after throw/roll and Simplified Chinese drift. |
| 2026-05-24 | `01_means_dative_anchor` / `mit` | 85 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `mit` drift scan + spot audit + full corpus dry-run pass | Fifth continuation batch completed without required rewrites after generation; vehicle and instrument spot checks were clean. |
| 2026-05-24 | `01_means_dative_anchor` / `mit` | 100 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | full targeted `mit` drift scan + spot audit + full corpus dry-run pass | Final batch generated cleanly; audit triggered targeted rewrites for older `033` ball phrasing plus new `096` book phrasing and `100` airplane phrasing. |
| 2026-05-24 | `01_means_dative_anchor` / `bei` | 10 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `bei` drift scan + spot audit + full corpus dry-run pass | First pass exposed bad Japanese location particles for static activity; generator validation and notes were tightened, then the full 10-file audit batch was regenerated cleanly. |
| 2026-05-24 | `01_means_dative_anchor` / `bei` | 25 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `bei` drift scan + spot audit + full corpus dry-run pass | First 15-file continuation batch completed without required rewrites after generation; static-near and person-place patterns remained stable. |
| 2026-05-24 | `01_means_dative_anchor` / `bei` | 40 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `bei` drift scan + spot audit + full corpus dry-run pass | Second 15-file continuation batch completed without required rewrites after generation; static-near and person-place patterns remained stable. |
| 2026-05-24 | `01_means_dative_anchor` / `bei` | 55 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `bei` drift scan + spot audit + full corpus dry-run pass | Third 15-file continuation batch completed without required rewrites after generation; static-near and person-place patterns remained stable. |
| 2026-05-24 | `01_means_dative_anchor` / `bei` | 70 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `bei` drift scan + spot audit + full corpus dry-run pass | Fourth 15-file continuation batch completed without required rewrites after generation; static-near and person-place patterns remained stable. |
| 2026-05-24 | `01_means_dative_anchor` / `bei` | 100 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | full targeted `bei` drift scan + spot audit + full corpus dry-run pass | Final two continuation batches completed without required rewrites after generation; the full `bei` set remained stable under the tightened static-vs-place constraints. |
| 2026-05-24 | `01_means_dative_anchor` / `aus` | 10 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `aus` drift scan + spot audit + full corpus dry-run pass | First pass exposed a format failure and mixed window semantics in `209`; generator validation and notes were tightened, then the window file was regenerated cleanly. |
| 2026-05-24 | `01_means_dative_anchor` / `aus` | 25 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `aus` drift scan + spot audit + full corpus dry-run pass | First 15-file continuation batch completed without required rewrites after generation; inside-source and take-out patterns remained stable. |
| 2026-05-24 | `01_means_dative_anchor` / `aus` | 40 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `aus` drift scan + spot audit + full corpus dry-run pass | Second 15-file continuation batch completed without required rewrites after generation; source-only movement and take-out patterns remained stable, including window and door exits. |
| 2026-05-24 | `01_means_dative_anchor` / `aus` | 55 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `aus` drift scan + spot audit + full corpus dry-run pass | Third 15-file continuation batch exposed weak Japanese climb-out phrasing in window files; the validator was tightened and affected window files were regenerated cleanly before acceptance. |
| 2026-05-24 | `01_means_dative_anchor` / `aus` | 70 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `aus` drift scan + spot audit + full corpus dry-run pass | Fourth 15-file continuation batch completed cleanly under the tightened window validator; source-exit and container-extraction patterns remained stable. |
| 2026-05-24 | `01_means_dative_anchor` / `aus` | 85 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `aus` drift scan + spot audit + full corpus dry-run pass | Fifth 15-file continuation batch exposed a second weak Japanese climb-out variant in window files; the validator was extended to reject both climb-up and generic climb-out drift, and the affected window file was regenerated cleanly before acceptance. |
| 2026-05-24 | `01_means_dative_anchor` / `aus` | 100 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | full targeted `aus` drift scan + spot audit + full corpus dry-run pass | Final continuation batch completed without further rewrites after generation; the full `aus` set remained stable under the tightened window-source and source-only movement constraints. |
| 2026-05-25 | `01_means_dative_anchor` / `von` | 10 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `von` drift scan + spot audit + full corpus dry-run pass | Audit batch clean; three subclusters added (surface-off, place-of-origin, person-origin) with dedicated drift guards for aus-drift, beim-drift, vom-contraction, ownership-drift, and container-interior-phrasing. |
| 2026-05-25 | `01_means_dative_anchor` / `von` | 25 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `von` drift scan + spot audit + full corpus dry-run pass | First 15-file continuation batch completed without required rewrites; kitchen and city source patterns remained stable. |
| 2026-05-25 | `01_means_dative_anchor` / `von` | 40 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `von` drift scan + spot audit + full corpus dry-run pass | Second 15-file continuation batch completed without required rewrites; teacher-person and floor-surface patterns remained stable. |
| 2026-05-25 | `01_means_dative_anchor` / `von` | 55 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `von` drift scan + spot audit + full corpus dry-run pass | Third 15-file continuation batch completed without required rewrites; house-source and city-source patterns remained stable. |
| 2026-05-25 | `01_means_dative_anchor` / `von` | 70 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `von` drift scan + spot audit + full corpus dry-run pass | Fourth 15-file continuation batch had one format failure in `362_von_doctor_source` (DeepSeek output glitch, all 4 pairs rendered as single lines); regenerated cleanly on retry. |
| 2026-05-25 | `01_means_dative_anchor` / `von` | 85 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `von` drift scan + spot audit + full corpus dry-run pass | Fifth 15-file continuation batch completed without required rewrites; garden-source and kitchen-source patterns remained stable without aus-drift. |
| 2026-05-25 | `01_means_dative_anchor` / `von` | 100 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | full targeted `von` drift scan + spot audit + full corpus dry-run pass | Final batch completed without required rewrites; full drift scan of all 100 von files found no aus-drift, vom-contraction, ownership-drift, or container-interior phrasing. |
| 2026-05-25 | `01_means_dative_anchor` / `zu` | 10 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `zu` drift scan + spot audit + full corpus dry-run pass | Audit batch clean; three subclusters added (person-destination, place-destination, object-destination) with drift guards for zum/zur-contraction, nach-with-article, in-accusative-endpoint, aus/von/bei-drift, and static-location forms. |
| 2026-05-25 | `01_means_dative_anchor` / `zu` | 25 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `zu` drift scan + spot audit + full corpus dry-run pass | First 15-file continuation batch completed without required rewrites; girl-person and garden-place patterns remained stable. |
| 2026-05-25 | `01_means_dative_anchor` / `zu` | 40 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `zu` drift scan + spot audit + full corpus dry-run pass | Second 15-file continuation batch completed without required rewrites; window and gate object-destination patterns remained stable. |
| 2026-05-25 | `01_means_dative_anchor` / `zu` | 55 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `zu` drift scan + spot audit + full corpus dry-run pass | Third 15-file continuation batch had one API-level JSON error on `446_zu_school_place` (network glitch); regenerated cleanly on retry. |
| 2026-05-25 | `01_means_dative_anchor` / `zu` | 70 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `zu` drift scan + spot audit + full corpus dry-run pass | Fourth 15-file continuation batch had one format failure on `461_zu_door_place` (same single-line output glitch as von); regenerated cleanly on retry. |
| 2026-05-25 | `01_means_dative_anchor` / `zu` | 85 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `zu` drift scan + spot audit + full corpus dry-run pass | Fifth 15-file continuation batch completed without required rewrites; tree object-destination pattern stayed clean with no bei-nearby drift. |
| 2026-05-25 | `01_means_dative_anchor` / `zu` | 100 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | full targeted `zu` drift scan + spot audit + full corpus dry-run pass | Final batch completed without required rewrites; full drift scan of all 100 zu files found no zum/zur-contraction, nach-drift, in-accusative-drift, or static-location forms. |
| 2026-05-25 | `01_means_dative_anchor` / `nach` | 100 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `nach` drift scan + spot audit + full corpus dry-run pass | All 6 continuation batches completed without failures; city/direction/temporal rotation clean across all 100 files. |
| 2026-05-26 | `01_means_dative_anchor` / `seit` | 50 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `seit` drift scan + spot audit + full corpus dry-run pass | All batches completed without failures; ongoing-duration meaning stable, seit dem/seit der dative forms correct throughout. |
| 2026-05-26 | `01_means_dative_anchor` / `gegenüber` | 50 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | targeted `gegenüber` drift scan + spot audit + full corpus dry-run pass | All batches completed without failures; static opposite/across-from meaning stable, no bei-drift or movement verbs. |
| 2026-05-26 | `01_means_dative_anchor` / `seit` extension | 100 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | full corpus dry-run pass | Extended from 50 to 100 files (601–700) for consistency with other prepositions. |
| 2026-05-26 | `01_means_dative_anchor` / `gegenüber` extension | 100 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | full corpus dry-run pass | Extended from 50 to 100 files (701–800); files renumbered from 651–700 to 701–750, offset base corrected in spec function. **01_means_dative_anchor complete: 800 files total.** |
| 2026-05-26 | `02_receiver_dative` | 16 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | spot audit (4 files) + full corpus dry-run pass | 8 verbs: give/show/bring/send/lend (ditransitive) then help/answer/tell (pure dative). Receiver dative visibly marked in every German line. JP に particle consistent. Traditional Chinese throughout. |
| 2026-05-26 | `bridge_course` | 100 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | full scan (6 checks) + corpus dry-run pass | Bracket-annotation schema (new format, no [user]/[Ninereeds] tags). Group A (001–050) ditransitive 4-pair, Group B (051–070) ditransitive+genitive 5-pair, Group C (071–100) pure-dative 3-pair. Validator catches: SECTION headers, simplified 给/苹/玛/铅/篮/邻/个, uppercase article in EN answers, German in EN answer position. Corpus builder updated with check_grammar_file dispatcher. |
| 2026-05-26 | `03_place_static_dative` | 24 | DeepSeek V4 Flash via `meta/scripts/gen_grammar.py` | spot audit (4 files) + full corpus dry-run pass 945/945 | 8 two-way prepositions × 3 files each: auf/in/über/unter/neben/vor/hinter/zwischen, all in dative. Static location only — no movement verbs. Drift guards added to validator: accusative forms (in die/das/den, auf die/das/den, etc.) flagged, movement verbs (stellt/legt/geht in) flagged, must contain dative two-way prep. JP にある/にいる inanimate/animate distinction correct throughout. Traditional Chinese clean. |
