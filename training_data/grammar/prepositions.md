# German Preposition Inventory

Purpose: local inventory for grammar-curriculum generation.

Source reference consulted: Fluent in 3 Months, "German Prepositions - The
Ultimate Guide (with Charts)", updated 2025-10-23.

This file is not a learner explanation. It is a generation control file for
Ninereeds grammar corpus work.

---

## Generation Principle

The grammar corpus should be thorough, but not flat.

High-frequency structural prepositions should receive many examples. Rare,
formal, literary, or abstract prepositions should receive fewer examples and
should appear later.

Preferred unit:

- one generated file contains EN, DE, JP, ZH parallel lines
- `100 files per preposition` therefore means 100 examples per language inside
  parallel files
- do not create separate language files unless a later experiment explicitly
  tests language isolation

---

## Priority Tiers

### Tier 1: Core Spatial / Case-Learning Prepositions

These carry the main grammar intervention.

Target: about 100 files each before run_13 is considered complete enough.

| Preposition | Case behavior | Primary function | Corpus cluster |
|---|---|---|---|
| in | two-way | in / into | static, endpoint, contrast |
| auf | two-way | on / onto | static, endpoint, contrast |
| unter | two-way | under | static, endpoint, contrast |
| über | two-way | above / over / about | static, endpoint, contrast, later idiom |
| an | two-way | at / on vertical surface / to edge | static, endpoint, contrast |
| vor | two-way | in front of / before | static, endpoint, time later |
| hinter | two-way | behind | static, endpoint, contrast |
| neben | two-way | next to | static, endpoint, contrast |
| zwischen | two-way | between | static, endpoint, contrast |

Note: `entlang` has special behavior and should not be mixed into the first
two-way-preposition block.

### Tier 2: Core Always-Dative Anchors

These build the dative pathway before two-way contrast.

Target: 50-100 files each depending on usefulness.

| Preposition | Case behavior | Primary function | Corpus cluster |
|---|---|---|---|
| mit | dative | accompaniment / instrument / vehicle means | means_dative_anchor |
| bei | dative | at / near / at someone's place | means_dative_anchor, static |
| von | dative | from / of | source_path_destination, ownership |
| aus | dative | from / out of | source_path_destination |
| zu | dative | to / toward person or institution | source_path_destination |
| nach | dative | after / to city or direction | source_path_destination, time later |
| seit | dative | since / for | time later |
| gegenüber | dative | opposite | static relation |

### Tier 3: Core Always-Accusative Prepositions

These should come after plain accusative patient examples.

Target: 30-60 files each before broad review.

| Preposition | Case behavior | Primary function | Corpus cluster |
|---|---|---|---|
| durch | accusative | through / by means of | path |
| für | accusative | for | receiver/benefit contrast |
| ohne | accusative | without | relation contrast |
| gegen | accusative | against / toward | target/path |
| um | accusative | around / at time | path, time later |
| bis | accusative | until / up to | path, time later |

`entlang` should be separate because it can follow the noun and has mixed
behavior depending on position.

### Tier 4: Genitive / Formal / Later Prepositions

These should be late and smaller. They are useful but not the bottleneck.

Target: 10-30 files each, after dative/accusative routing is stable.

| Preposition | Case behavior | Primary function | Corpus cluster |
|---|---|---|---|
| wegen | genitive, often dative colloquially | because of | owner_genitive, later causal |
| während | genitive, often dative colloquially | during | time |
| trotz | genitive | despite | contrast |
| statt / anstatt | genitive | instead of | contrast |
| innerhalb | genitive | inside of | abstract/place |
| außerhalb | genitive | outside of | abstract/place |
| oberhalb | genitive | above | spatial formal |
| unterhalb | genitive | below | spatial formal |
| diesseits | genitive | on this side | spatial formal |
| jenseits | genitive | beyond / other side | spatial formal |
| beiderseits | genitive | on both sides | spatial formal |

### Tier 5: Dative Formal / Abstract

Useful later, but not early child-facing grammar.

Target: 5-20 files each if included.

| Preposition | Case behavior | Primary function | Notes |
|---|---|---|---|
| ab | dative | from time / from point | time/path |
| außer | dative | except for | contrast |
| dank | dative/genitive | thanks to | abstract causal |
| entgegen | dative | contrary to / toward | abstract/path |
| gemäß | dative | according to | formal |
| laut | dative/genitive | according to | formal |
| zufolge | dative, often postposition | according to | formal |

---

## Special Handling

### Two-Way Preposition Rule

Do not teach as "motion always equals accusative".

Teach as:

- static relation to the anchor: dative
- endpoint/change of relation to the anchor: accusative

Examples:

- `Der Becher ist auf dem Tisch.`
- `Emma stellt den Becher auf den Tisch.`
- `Die Kinder laufen im Garten.`
- `Die Kinder laufen in den Garten.`

### `über`

Split into at least three later subclusters:

- static spatial: `über dem Berg`
- endpoint/path: `über den Fluss`
- topic/about: `über den Hund sprechen`

Do not mix `about` with early spatial `above`.

### `entlang`

Handle separately.

Patterns:

- postposition with accusative: `die Straße entlang`
- preposition-like use may take dative in some registers: `entlang der Straße`

This is too irregular for early case scaffolding.

### Contractions

Teach after full article forms are stable.

Important contractions:

| Full form | Contraction |
|---|---|
| an das | ans |
| an dem | am |
| auf das | aufs |
| bei dem | beim |
| durch das | durchs |
| für das | fürs |
| in das | ins |
| in dem | im |
| über das | übers |
| um das | ums |
| unter das | unters |
| von dem | vom |
| vor das | vors |
| vor dem | vorm |
| zu dem | zum |
| zu der | zur |

Early files should prefer full forms first, then introduce contractions as
equivalent surface forms.

---

## Scale Recommendation

If using four-language parallel files:

| Tier | Prepositions | Files each | Approx files |
|---|---:|---:|---:|
| Tier 1 | 9 | 100 | 900 |
| Tier 2 | 8 | 50-100 | 400-800 |
| Tier 3 | 6 | 30-60 | 180-360 |
| Tier 4 | 11 | 10-30 | 110-330 |
| Tier 5 | 7 | 5-20 | 35-140 |

This is a large but reasonable grammar curriculum if generated and audited in
batches. Do not generate all tiers before testing Tier 1 + Tier 2.

