# Grammar Corpus Plan

Purpose: design a dedicated grammar-function corpus for Ninereeds.

This corpus is not topic-first. It is ordered by grammatical function, with
German case patterns as the main spine and Japanese particles as cross-reference
cues where they clarify the same relation. Topics such as home, school, food,
weather, and nature are example domains inside the grammar sequence, not the
ordering principle.

The immediate target is run_13: test whether grammar-function ordering improves
German dative/accusative behavior, spatial reasoning, and arithmetic echo
pressure when trained at 150M.

---

## Training Requirement

The grammar corpus only makes sense if Ninereeds sees the files in the designed
order.

Current `train.py` shuffles fixed-size training windows with `torch.randperm`.
That is deterministic when seeded, but it still destroys the intended curriculum
order. For grammar runs, training needs a sequential/no-shuffle mode:

- corpus builder emits files in grammar order
- training consumes windows in corpus order
- the same corpus and same checkpoint produce the same update order every run
- direct comparisons across run_13 variants are valid because data order is fixed

This is a run_13 prerequisite. Do not launch grammar training while window
shuffling is still active for the run.

---

## Core Hypothesis

Ninereeds has seen dative, accusative, spatial, and movement forms, but the
signals are mixed by topic order and by surface-form competition.

The grammar corpus should teach a learner rule first:

- dative = relation, receiver, location, source, accompaniment, means
- accusative = direct patient, simple target, movement endpoint
- genitive = ownership and attribute relation
- nominative = default subject frame, learned implicitly

This is not a complete German grammar. It is a productive retrieval scaffold.
The goal is to make the correct form easier to retrieve under production
pressure.

Japanese particles are not treated as one-to-one equivalents, but they provide
useful parallel cues:

| Function | German | Japanese cue | Notes |
|---|---|---|---|
| receiver / indirect object | dative | に | `Emma gives the boy a cup` |
| static existence location | dative with two-way prepositions | に | `The cup is on the table` |
| activity location | dative-like place relation | で | `Emma plays in the garden` |
| movement endpoint | accusative with two-way prepositions | に / へ | endpoint cue, not case-equivalent |
| direct object / patient | accusative | を | transitive verb patient |
| source | dative prepositions such as `von`, `aus` | から | origin relation |
| path / limit | prepositional relation | まで | endpoint boundary |
| accompaniment / instrument / means | dative preposition `mit` | と / で | person-with vs tool-by vs vehicle-by distinction |
| ownership / attribute | genitive or `von` relation | の | late, light block |

---

## Corpus Shape

Directory target:

```text
training_data/grammar/
```

Recommended file naming:

```text
01_dative_anchor_mit_DE.md
01_dative_anchor_mit_JP.md
01_dative_anchor_mit_ZH.md
01_dative_anchor_mit_EN.md
02_dative_receiver_give_DE.md
...
```

Each grammar unit should be small and explicit. One file should teach one
function or one contrast only.

Preferred file format:

```text
[user]Where is the cup?
[Ninereeds]The cup is on the table.
Der Becher ist auf dem Tisch.
コップはテーブルの上にある。
杯子在桌子上。
```

Use `[user]` / `[Ninereeds]` because the probe and live inference route through
that format. Plain prose can appear later as reinforcement, not as the first
teaching form.

Each file should contain 4-8 short pairs:

- one English prompt
- one response with EN, DE, JP, ZH parallel lines
- no long explanation
- no metalinguistic grammar lecture in the response unless the file is explicitly
  a contrast file
- repeat the key surface form enough times to anchor retrieval

---

## Sequence

### 0. Bridge: relation words

Goal: teach the abstract words needed to talk about grammar without overloading
the model.

Functions:

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

Example forms:

- `A receiver gets something.`
- `A source is where movement begins.`
- `A target is where movement points.`
- `A place is where something is.`

This block can be English-heavy with multilingual support lines. It should be
short. The corpus should teach grammar through examples, not through definitions.

### 1. Always-dative anchors

Goal: build the dative retrieval pathway before introducing ambiguous two-way
prepositions.

German prepositions:

- `mit`
- `bei`
- `von`
- `aus`
- `zu`
- `nach`
- `seit`
- `gegenüber`

Example patterns:

- `mit dem Hund`, `mit der Katze`, `mit dem Kind`
- `mit dem Bus fahren`
- `mit dem Hammer arbeiten`
- `mit dem Ball spielen`
- `bei dem Baum`, `bei der Schule`, `bei dem Haus`
- `von dem Tisch`, `von der Bank`, `von dem Fenster`
- `aus dem Garten`, `aus der Küche`, `aus dem Zimmer`
- `zu dem Kind`, `zu der Tür`, `zu dem Tor`

Japanese cross-cues:

- `と` for accompaniment
- `で` for instrument, means, or vehicle
- `に` for destination/person relation
- `から` for source

Keep this block concrete and repetitive. It is the grammar equivalent of
arithmetic Phase A: exact retrieval first.

`mit` deserves a small internal split:

- accompaniment: `Emma geht mit dem Hund.`
- instrument: `Gran arbeitet mit dem Hammer.`
- vehicle/means: `Taro fährt mit dem Bus.`

All three forms are dative in German, but the Japanese cue differs by function.
This gives more sentence variety without changing the case target.

### 2. Dative receiver / indirect object

Goal: connect dative with recipient and benefit.

German functions:

- `dem Kind geben`
- `der Frau zeigen`
- `dem Hund helfen`
- `dem Lehrer antworten`
- `Emma gibt dem Jungen den Apfel`
- `Taro zeigt dem Mann das Buch`
- `Gran hilft dem Arzt`

Japanese cross-cue:

- `に`

Topics:

- food: apple, bread, water
- school: book, pencil, teacher
- home: cup, bowl, chair
- people: `dem Jungen`, `dem Mann`, `dem Arzt`, `der Frau`, `dem Kind`

Contrast should be postponed until after the positive pattern is stable. Start
with receiver-only examples before adding direct-object + indirect-object pairs.
Avoid bare proper-name receivers such as `Emma gibt Taro den Apfel` in the first
receiver block. The sentence is grammatical, but the dative receiver is not
visibly marked. Early examples should make the dative article obvious:
`dem Jungen`, `dem Mann`, `dem Arzt`, `der Frau`, `dem Kind`.

### 3. Static location

Goal: teach dative as location/state under two-way prepositions.

German prepositions:

- `in`
- `auf`
- `unter`
- `über`
- `an`
- `vor`
- `hinter`
- `neben`
- `zwischen`

Example patterns:

- `Der Becher ist auf dem Tisch.`
- `Emma sitzt in der Küche.`
- `Die Wolke ist über dem Berg.`
- `Der Hund liegt unter der Bank.`
- `Taro steht neben dem Baum.`

Japanese cross-cues:

- `にある` for existence/location
- `で` for activity location
- `の上に`, `の下に`, `の前に`, `の後ろに`, `の隣に`

This block is valuable beyond language. It teaches spatial relations and should
improve probes such as `A cloud is above the mountain`.

### 4. Change of state and becoming

Goal: teach relation/state change without confusing it with endpoint movement.

German examples:

- `Der Baum wird größer.`
- `Taro wacht auf.`
- `Emma wird eine Schwester.`
- `Das Wasser wird warm.`
- `Der Teig wird Brot.`

Japanese cross-cues:

- `になる`
- `くなる`
- `起きる`

Notes:

- German case pressure is lower here than in prepositional dative, but the
  semantic function matters: the learner sees state transition as relation
  change, not object transfer.
- Use this as a bridge into causal stories later.

### 5. Plain accusative patient

Goal: teach direct object / acted-on patient before movement endpoints.

German examples:

- `Emma sieht den Hund.`
- `Taro trägt den Korb.`
- `Gran schneidet den Apfel.`
- `Emma öffnet die Tür.`
- `Taro nimmt das Buch.`

Japanese cross-cue:

- `を`

Keep this block separate from dative receiver at first. The target pattern is
simple: action points at the object.

### 6. Accusative movement endpoint

Goal: teach two-way prepositions with movement into/onto/under a target.

German examples:

- `Emma geht in die Küche.`
- `Taro legt den Becher auf den Tisch.`
- `Der Hund läuft unter die Bank.`
- `Gran hängt den Mantel an die Tür.`
- `Der Ball rollt hinter den Stuhl.`

Japanese cross-cues:

- `に`
- `へ`
- `の上に置く`
- `の下へ走る`

The learner rule:

- static place: `auf dem Tisch`
- movement endpoint: `auf den Tisch`

Do not mix this with source/path examples until this contrast is stable.

### 7. Static vs movement contrast

Goal: make the two-way-preposition distinction explicit.

Use paired examples in the same mini-domain:

- `Der Becher ist auf dem Tisch.`
- `Emma stellt den Becher auf den Tisch.`
- `Der Hund ist unter der Bank.`
- `Der Hund läuft unter die Bank.`
- `Taro ist in der Küche.`
- `Taro geht in die Küche.`

Japanese helps here only partially. The contrast should be taught mainly through
German form and English meaning:

- `is on` vs `puts onto`
- `is in` vs `goes into`
- `is under` vs `runs under`

### 8. Source, path, and destination chains

Goal: handle sentences where dative and accusative-like destination cues appear
together.

German examples:

- `Ich fahre von meinem Haus zum Kino.`
- `Emma geht aus der Küche in den Garten.`
- `Taro läuft vom Baum zur Bank.`
- `Der Hund kommt aus dem Haus und läuft unter den Tisch.`

Japanese cross-cues:

- `から`
- `まで`
- `へ`
- `に`

This block should come after static/movement contrast. It is inherently mixed
and will be confusing if introduced early.

### 9. Possession and genitive

Goal: teach ownership and attribute relation lightly.

German examples:

- `Emmas Becher`
- `der Becher von Emma`
- `die Farbe des Blattes`
- `die Tür des Hauses`

Japanese cross-cue:

- `の`

Genitive should be late and small. It is useful, but it is not the bottleneck.
For Ninereeds, `von` possession may be more productive than formal genitive.

### 10. Mixed review stories

Goal: put the grammar into grounded events after exact retrieval is established.

Use short, concrete stories with repeated relation patterns:

- Emma gives the boy an apple.
- Taro puts the apple on the table.
- The apple is on the table.
- Biscuit runs under the bench.
- Gran takes the apple from the table.

This block should be narrative reinforcement, not the initial teaching signal.

---

## DeepSeek Generation Plan

Generate one cluster at a time. Do not ask DeepSeek for the whole grammar corpus
in one pass.

For each cluster:

1. Write a cluster prompt with the exact grammatical target.
2. Specify allowed names and objects.
3. Require four-language parallel responses.
4. Require short `[user]` / `[Ninereeds]` pairs.
5. Validate tag counts, line counts, and forbidden drift.
6. Only then move to the next cluster.

Initial cluster targets:

| Cluster | Files | Purpose |
|---|---:|---|
| relation_bridge | 4 | relation vocabulary |
| dative_anchors | 24 | always-dative prepositions |
| dative_receiver | 16 | recipient / indirect object |
| static_location | 24 | spatial dative |
| change_state | 12 | becoming / state change |
| accusative_patient | 16 | direct object |
| accusative_endpoint | 24 | movement endpoint |
| static_vs_endpoint | 18 | contrast pairs |
| source_path_destination | 16 | mixed path chains |
| possession_genitive | 8 | ownership |
| review_stories | 12 | grounded reinforcement |

Total target: about 174 files. This is large enough to create a grammar signal
but small enough to audit.

---

## Validation Checklist

Each file must pass:

- exactly the intended number of `[user]` and `[Ninereeds]` tags
- no missing language line in a response
- German case form matches the cluster target
- Japanese particle is plausible for the intended function
- Traditional Chinese is used for ZH
- no romaji in JP
- no unrelated grammar point introduced early
- no long explanation unless the file is a contrast file

Corpus-level checks:

- count `über dem` vs `über den` by function, not globally
- count `in der Küche` static vs `in die Küche` movement
- count always-dative anchors before two-way-preposition files
- verify grammar files appear before narrative review files
- verify training uses sequential/no-shuffle mode

---

## Run 13 Success Signals

Primary probes:

- `Die Wolke ist über dem Berg.`
- `Das Kind geht in den Garten.`
- `Emma gibt dem Jungen den Apfel.`
- `Der Becher ist auf dem Tisch.`
- `Emma stellt den Becher auf den Tisch.`

Secondary probes:

- Japanese location output uses `にある` or equivalent location phrasing.
- Japanese direct object output uses `を`.
- Spatial relation outputs improve in English and German.
- Arithmetic echo pressure does not worsen.

Do not promote a checkpoint on grammar probes alone. Shaped score and loop count
remain promotion gates.
