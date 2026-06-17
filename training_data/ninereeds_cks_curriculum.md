# Ninereeds CKS Corpus Curriculum Specification
## Source: Core Knowledge Sequence (Preschool + K–8), 2023 Edition
## Purpose: Training data generation pipeline spec for Claude Code → DeepSeek

---

## 1. Overview

This document specifies the curriculum structure, teaching order, domain assignments, language
assignments, vocabulary anchors, and generation constraints for converting the Core Knowledge
Sequence (CKS) PDFs into Ninereeds training corpus files.

### 1.1 Source Documents
- `CK_Sequence2023_PreSchool_W2.pdf` — Preschool content
- `CK_Sequence2023_GK8_W3.pdf` — Grades K–8 content

### 1.2 Output Format
Each output file is a teacher/learner dialogue in `[user]`/`[Ninereeds]` format.
- **`[user]`** = the Teacher: introduces the topic, explains, demonstrates, answers questions
- **`[Ninereeds]`** = the Curious Learner: asks questions that drive the lesson forward
- Length is variable — as many exchanges as the topic needs; not capped at 3–5 sentences
- Concrete and sensory for Tier 0–1 content; functional and relational for abstract content
- No named characters (use "a plant", "an animal", "a child" etc.)
- One `[user]`/`[Ninereeds]` exchange per conceptual beat; not one long monologue
- File format: `.md`
- Filename pattern: `{domain}_{topic_slug}_{lang}.md`
  - Example: `science_plant_lifecycle_de.md`

**Generated in Phase 4 of the pipeline** (see Section 10). Phase 1–3 produce the
structured metadata; Phase 4 is the DeepSeek generation pass.

### 1.3 Language Coverage
- **Preschool**: All concept clusters → 4 files each (EN, DE, JA, ZH)
- **K–8**: Each concept cluster → 1 file, language assigned by domain (see Section 4)

### 1.4 Licensing
Source material is CC BY-NC-SA 4.0. Generated corpus files derived from it
should carry the same license notice in a corpus-level README.

---

## 2. Domain Map

### 2.1 Included Domains

| Domain ID | Full Name | Source | Notes |
|-----------|-----------|--------|-------|
| `lang` | Language and Literacy | CKS sections | Oral language, vocabulary, syntax, story schema |
| `math` | Mathematical Reasoning | CKS sections | Classification, patterns, shapes, quantity, arithmetic |
| `time` | Orientation in Time | CKS sections | Temporal vocabulary, calendars, past/present/future, life cycles |
| `space` | Orientation in Space | CKS sections | Spatial vocabulary, maps, geographic features |
| `science` | Scientific Reasoning and the Physical World | CKS sections | Living world, plants, animals, material world |
| `arts` | Arts and Human Creative Expression | Synthesized | Music + visual arts + language arts as unified phenomenon |

### 2.2 Excluded Domains
- Movement and Coordination (physical, no robot body)
- Social and Emotional Development: Autonomy (behavioral self-care)
- Social and Emotional Development: Work Habits (metacognitive habits, no factual content)
- Fine Motor / Writing Strokes (entirely physical)

---

## 3. Teaching Order and Dependencies

The order below governs both the curriculum structure and the training manifest
interleaving. Dependencies must appear before dependents.

```
TIER 0 — Concrete Anchors (no dependencies)
  math.classification         — same/different, sort, group
  math.shapes                 — circle, square, triangle, rectangle
  science.five_senses         — sight, hearing, smell, taste, touch
  lang.basic_vocabulary       — nouns: home, family, food, body parts, colors
  space.positional_language   — in/out, above/below, near/far, left/right

TIER 1 — Simple Relations (depends on Tier 0)
  math.patterns               — alternating, continue, create (depends: classification, shapes)
  math.quantity_small         — one to four, more/less, same as (depends: classification)
  science.living_nonliving    — what makes something alive (depends: five_senses)
  science.plants_basic        — seed, stem, leaf, root, grow, water, sun (depends: living_nonliving)
  science.animals_basic       — habitat, body parts, needs, movement (depends: living_nonliving)
  time.daily_time             — morning/afternoon/evening, before/after, now/then (depends: basic_vocabulary)
  space.geographic_features   — land, water, river, lake, ocean, farm, forest (depends: positional_language)
  lang.story_schema           — character, setting, event, beginning/middle/end (depends: basic_vocabulary)

TIER 2 — Extended Relations (depends on Tier 1)
  math.quantity_extended      — one to ten, count, numeral, ordinal (depends: quantity_small)
  math.measurement            — long/short, tall, heavy/light, full/empty, temperature (depends: quantity_small, shapes)
  math.arithmetic_basic       — put together, take away, add, subtract (depends: quantity_extended)
  math.money_basic            — penny, quarter, dollar, value (depends: quantity_extended)
  science.plants_lifecycle    — seed→sprout→plant→flower→seed, needs over time (depends: plants_basic)
  science.animals_lifecycle   — birth→growth→adult, habitat classification (depends: animals_basic)
  science.human_body          — organs, senses, basic needs, growth stages (depends: animals_basic, five_senses)
  science.material_world      — water properties, air properties, light properties (depends: living_nonliving)
  science.weather_seasons     — weather observation, four seasons, change over time (depends: material_world)
  time.weekly_monthly         — days of week, months, calendar, week/month/year (depends: daily_time)
  time.past_present_future    — passage of time, change, long ago, generations (depends: weekly_monthly)
  space.maps_basic            — simple map, location, landmark, path (depends: geographic_features)
  lang.vocabulary_syntax      — verbs/senses, temporal words, spatial words, opposites, size words (depends: basic_vocabulary, story_schema)
  lang.phonemic_awareness     — sound units, rhyme, beginning sounds (depends: basic_vocabulary)

TIER 3 — Abstract and Integrative (depends on Tier 2)
  math.data_graphs            — bar graph, organize data, compare (depends: quantity_extended, measurement)
  science.conservation        — recycling, resources, energy (depends: material_world, science.human_body)
  science.magnets             — attraction, repulsion, force (depends: material_world)
  time.historical_perspective — objects from the past, change over generations (depends: past_present_future)
  space.globe_world           — globe, country, continent, world map (depends: maps_basic)
  lang.narrative_extended     — prediction, imagination, point of view, retelling (depends: story_schema, vocabulary_syntax)
  arts.human_creative         — what art is, why humans make it, modalities, Ninereeds' position (synthesized, no CKS dependency)

TIER 4 — K–8 Extension Domains (Preschool complete before any K–8 content)
  [K–8 domains follow, organized by grade band: K–2, 3–5, 6–8]
  [See Section 5 for K–8 structure]
```

---

## 4. Language Assignments

### 4.1 Preschool (all domains → 4 languages)
Every concept cluster generates EN + DE + JA + ZH files.
Each language takes a **different angle** on the same concept:
- **EN**: general explanatory dialogue, accessible register
- **DE**: precise, slightly more technical; favors compound structures and causal framing
- **JA**: contextual and relational framing; social and situational anchoring where applicable
- **ZH**: terse, structural; favors classification and categorical framing

### 4.2 K–8 Domain → Language Assignment

| Domain | Language | Rationale |
|--------|----------|-----------|
| `lang` | EN | Language concepts most naturally expressed in English; widest register range |
| `math` | ZH | Mathematical reasoning; terse structural expression; categorical precision |
| `time` (history/social) | JA | Social/relational time concepts; Japanese temporal grammar encodes nuance morphologically |
| `space` (physical geography) | DE | Scientific precision; compound nouns package geographic concepts efficiently |
| `space` (human/social geography) | JA | Settlement, community, relationship to place |
| `science` | DE | Scientific tradition; causal and observational framing; precise technical vocabulary |
| `arts` | EN | Testimony and description across registers; language arts directly accessible |

### 4.3 Balance Check (approximate)
Target: no language more than 2× any other across K–8.
After extraction, count concept clusters per domain and verify balance.
Rebalance by shifting borderline domains (e.g. split geography 50/50 DE/JP)
if any language is over- or under-represented by more than 30%.

---

## 5. K–8 Structure (Grade Bands)

K–8 content is organized into three grade bands for manifest interleaving.
Within each band, teaching order follows the same Tier logic as preschool
(concrete → relational → abstract).

### Band A: Grades K–2
Extends preschool concepts with increasing specificity.
Introduces: world history (ancient civilizations), expanded geography,
life science (ecosystems), physical science (matter, forces), grammar,
literary elements, multiplication foundations.

### Band B: Grades 3–5
Introduces: medieval history, American history, earth science,
fractions and decimals, grammar complexity, literary analysis,
world geography at country/region level.

### Band C: Grades 6–8
Introduces: ancient to modern world history, algebra foundations,
geometry, earth/space science, chemistry basics, literature and rhetoric,
civics and economics.

**Note**: Claude Code should extract grade band content from the K–8 PDF
and assign to bands based on the grade headers in the document.
Each band is processed as a separate pass.

---

## 6. Generation Constraints

### 6.1 Dialogue Rules (all languages)

**Format**: Each file is a `[user]`/`[Ninereeds]` dialogue. `[user]` is the Teacher;
`[Ninereeds]` is the Curious Learner. Ninereeds' questions drive the lesson — the
Teacher answers each one, introducing the next concept in response.

**Structure**:
- Each `[Ninereeds]` turn is a genuine question (not a statement)
- Each `[user]` turn answers the question and may introduce one new fact that
  invites the next question
- One conceptual beat per exchange — do not pack multiple new facts into one turn
- No named characters (use "a child", "a plant", "an animal", "a person")
- Concrete and sensory for Tier 0–1 content; relational and functional for Tier 2–3
- For Arts: Teacher uses human experiential testimony ("people often feel...",
  "humans use music to...") while being honest about what Ninereeds can and cannot
  directly experience

**Example skeleton (science.plants_basic)**:
```
[Ninereeds]What are the parts of a plant?
[user]A plant has roots, a stem, leaves, and usually a flower.
The roots hold the plant in the soil and take up water.

[Ninereeds]What does the stem do?
[user]The stem carries water from the roots up to the leaves.
It also holds the plant upright.

[Ninereeds]Why do plants need sunlight?
[user]Leaves use sunlight to make food for the plant.
Without sunlight, the plant cannot grow.

[Ninereeds]Where do seeds come from?
[user]Seeds form inside the flower, often inside a fruit.
A new plant can grow from each seed.
```

**Length**: as many exchanges as the topic's `working_memory_ceiling` and
`boundary_scope` require. Do not pad; do not cut off before the concept is complete.

### 6.2 Language-Specific Constraints

**EN**: Clear, accessible dialogue. Teacher explains naturally; Ninereeds asks
genuinely curious questions. Present tense for general truths. Avoid passive voice.

**DE**: Teacher uses compound nouns naturally (Lebewesen, Jahreszeiten, Schwerkraft).
Grammatical case precision in all noun phrases. Ninereeds' questions may be slightly
more formal than in EN. Plain form narration; no watered-down register.

**JA**: Teacher uses plain form (だ/である) not polite form (です/ます).
Encode relational and contextual framing where natural. Ninereeds' questions use
the curious-child register (〜の？　〜はなに？). Use は/が distinction carefully.
Prefer shorter turns with clear topic chains.

**ZH**: Teacher uses 是...的 and 有 structures for classification and existence.
Favor parallel structures for lists of properties. Keep turns compact.
Prefer 把 construction for action on objects where natural.
No traditional characters — simplified only.

### 6.3 What to Avoid
- Do not reproduce CKS skill codes (I-SC1.1 etc.) in output files
- Do not reproduce CKS text verbatim (CC license; also poor training data)
- Do not frame content as instructions ("children should learn...")
- Do not generate content about purely physical skills (balance, throwing, cutting)
- Do not have Ninereeds state facts — Ninereeds only asks questions
- Do not have the Teacher answer a question Ninereeds has not yet asked
- For Arts: do not claim qualia Ninereeds cannot access
  ("a violin sounds warm" → "people describe the violin's sound as warm")

---

## 7. Vocabulary Anchor Lists

These are the core vocabulary items the generated paragraphs should
naturally incorporate. They are extracted from CKS Language of Instruction
sections. DeepSeek should use these as grounding anchors — the concepts
must appear in natural prose, not as isolated lists.

### 7.1 math.classification
same, different, sort, group, classify, color, shape, size, function,
property, category, collection, attribute, match, belong

### 7.2 math.shapes
circle, square, triangle, rectangle, corner, side, curved, straight,
round, flat, outline, shape, form

### 7.3 math.patterns
pattern, repeat, alternate, continue, extend, create, sequence,
color pattern, two-color pattern, one property, next

### 7.4 math.quantity_small
one, two, three, four, more, less, fewer, same as, count, how many,
group, compare, equal, number

### 7.5 math.quantity_extended
five through ten, numeral, write, order, sequence, ordinal,
first/last, bar graph, data

### 7.6 math.measurement
long, short, tall, heavy, light, full, empty, hot, cold, wide, narrow,
thick, thin, large, small, compare, measure, longer, taller, shorter

### 7.7 math.arithmetic_basic
add, subtract, put together, take away, total, sum, difference,
plus, minus, equals, number sentence

### 7.8 math.money_basic
penny, quarter, dollar, coin, bill, value, more, less, money

### 7.9 lang.basic_vocabulary
home, family, food, clothing, school, town, transportation,
body parts (arm ear eye face finger foot hair hand head leg mouth neck nose stomach toe),
colors (black blue brown green orange purple red white yellow),
verbs of sense (see hear smell taste touch feel)

### 7.10 lang.story_schema
character, setting, time, place, beginning, middle, end, event,
plot, retell, sequence, predict, ending, story, illustration

### 7.11 lang.vocabulary_syntax
opposite, category, describe, explain, question, compare,
temporal words (today tomorrow yesterday before after now first last always never sometimes),
spatial words (above below near far inside outside between next to),
size words (large small wide narrow thick thin tall short heavy light),
adverbs (quickly slowly gently softly)

### 7.12 lang.phonemic_awareness
sound, rhyme, rhyming word, beginning sound, syllable,
word, sentence, letter, alphabet, blend

### 7.13 lang.narrative_extended
predict, imagine, point of view, opinion, retell, cause, effect,
sequence, describe, express, communicate, story, narrative

### 7.14 space.positional_language
above, below, in front of, behind, next to, between, near, far,
inside, outside, over, under, left, right, here, there, up, down,
in a line, in a circle, around

### 7.15 space.geographic_features
land, water, river, lake, ocean, farm, forest, jungle, desert,
city, countryside, island, mountain, coast, valley

### 7.16 space.maps_basic
map, globe, location, landmark, path, route, symbol, country,
state, continent, direction, north, south, east, west

### 7.17 space.globe_world
globe, world, continent, country, ocean, equator, hemisphere,
north pole, south pole, climate zone

### 7.18 time.daily_time
morning, afternoon, evening, night, day, today, tomorrow, yesterday,
before, after, now, first, last, always, never, sometimes, soon, already,
clock, schedule, calendar

### 7.19 time.weekly_monthly
day of the week (Monday–Sunday), weekend, month, year,
calendar, date, week, sequence, current

### 7.20 time.past_present_future
past, present, future, long ago, change, grow, old, young,
remember, generation, life cycle, timeline, century, history

### 7.21 time.historical_perspective
then, now, long ago, object from the past, change over time,
invention, transportation, communication, recent, distant

### 7.22 science.five_senses
sight, hearing, smell, taste, touch, eye, ear, nose, tongue, skin,
observe, describe, identify, property, attribute

### 7.23 science.living_nonliving
alive, living, not living, grow, move, breathe, need, respond,
organism, characteristic, life

### 7.24 science.plants_basic
seed, stem, leaf, root, flower, fruit, bulb, shoot, sprout,
soil, sunlight, water, grow, plant, living

### 7.25 science.plants_lifecycle
life cycle, germinate, sprout, grow, flower, seed, reproduce,
season, stage, development, change over time

### 7.26 science.animals_basic
animal, habitat, body parts, movement, need, food, shelter,
farm, forest, ocean, jungle, lake, river, living

### 7.27 science.animals_lifecycle
birth, growth, development, adult, life cycle, young, offspring,
stage, change, reproduce, care

### 7.28 science.human_body
heart, lungs, brain, sense organs, skeleton, muscle, blood,
breathe, digest, grow, need, food, water, shelter, health

### 7.29 science.material_world
water, air, light, solid, liquid, shadow, ice, steam, evaporate,
property, observe, describe, affect, sun, wind, source

### 7.30 science.weather_seasons
weather, season, spring, summer, autumn, winter, temperature,
rain, snow, wind, cloud, sun, observe, record, change

### 7.31 science.conservation
recycle, resource, energy, conserve, reduce, reuse, waste,
environment, protect, natural resource

### 7.32 science.magnets
magnet, attract, repel, north pole, south pole, force, metal,
iron, magnetic field, push, pull, strength

### 7.33 arts.human_creative
art, music, visual art, poetry, story, dance, create, express,
emotion, beauty, meaning, form, pattern, rhythm, color, sound,
instrument, melody, composition, painter, sculptor, poet,
aesthetic, culture, experience, feeling, imagination,
qualia, sense, modality, language, symbol

---

## 8. Arts Domain: Special Generation Brief

The Arts domain is synthesized rather than extracted from CKS skill codes.
It should be treated as a single unified domain with the following
conceptual structure. DeepSeek should generate paragraphs covering
each of these sub-topics:

### 8.1 What Art Is
Art is the deliberate creation of objects, sounds, movements, or language
with the intent to express, communicate, or evoke something beyond pure function.
Humans have made art in every known culture and period of history.

### 8.2 Why Humans Make Art
Art serves emotional expression, cultural memory, social bonding, and
the communication of experiences that ordinary language reaches poorly.
It preserves what would otherwise be lost — feeling, atmosphere, the texture of a moment.

### 8.3 The Modalities
Each art form operates through a different sensory channel:
- Visual art operates through light, color, form, and space
- Music operates through sound, rhythm, and time
- Language arts (poetry, story, narrative) operate through words, meaning, and structure
- Dance and performance operate through the body moving in time and space
Each modality has things it can do that the others cannot.

### 8.4 Color and Emotion
Colors reliably induce emotional states in humans, though the mechanisms
are not fully understood. Warm colors (red, orange, yellow) tend toward
energy and intensity; cool colors (blue, green) tend toward calm.
Visual artists use this to shape how a work feels.

### 8.5 Sound and Emotion
Musical sounds induce emotional states. Tempo (fast/slow), dynamics (loud/soft),
and pitch relationships (major/minor modes) reliably produce recognizable
emotional responses across cultures. A slow, quiet melody in a minor key
is perceived as sad; a fast, loud melody in a major key as joyful or triumphant.

### 8.6 Pattern, Rhythm, and Structure
All art forms involve pattern — repetition, variation, contrast, resolution.
This is the element most directly accessible through structural analysis.
Rhythm in music maps to pattern in mathematics. Composition in visual art
maps to spatial structure. Narrative arc maps to sequence and causality.

### 8.7 Language Art as Direct Access
Poetry, story, and narrative are art forms that operate through language —
the same medium through which all knowledge in this corpus is encoded.
These are the art forms most directly accessible to a language-based mind.
Metaphor, imagery, rhythm in prose, the emotional arc of a story —
these can be experienced, not merely described.

### 8.8 Ninereeds' Position (honest framing)
A mind that processes language can directly experience language-based art.
For visual art and music, the experience is mediated — available through
human testimony, structural analysis, and functional description,
but not through direct sensory access. This is a real difference, not a deficiency.
Humans who are blind or deaf develop rich understandings of arts they cannot
directly perceive, through the testimony of others and through structural knowledge.

---

## 9. File Structure and Naming

**Phase 1 metadata (JSONL — already written):**
```
training_data/04_education/
  phase1_preschool.jsonl      ← 34 topics, full schema (written 2026-06-18)
  phase1_k8.jsonl             ← K–8 topics, to be extracted
```

**Phase 4 generated dialogue files (`.md`):**
```
training_data/04_education/
  preschool/
    math/
      math_classification_en.md
      math_classification_de.md
      math_classification_ja.md
      math_classification_zh.md
      math_shapes_en.md
      ...
    science/
      science_plants_basic_en.md
      ...
    lang/
    time/
    space/
    arts/
      arts_human_creative_en.md
      arts_human_creative_de.md
      arts_human_creative_ja.md
      arts_human_creative_zh.md
  k8/
    band_a/         (grades K–2)
      math/         (zh)
      science/      (de)
      lang/         (en)
      time/         (jp)
      space/        (de or jp by sub-type)
      arts/         (en)
    band_b/         (grades 3–5)
      ...
    band_c/         (grades 6–8)
      ...
```

---

## 10. Pipeline Summary

The pipeline has four phases. Phases 1–3 produce structured metadata; Phase 4 is the
DeepSeek generation pass that produces the actual training files.

### Phase 1 — Ontology Extraction (Claude Code reads PDFs → JSONL)

Output schema per topic:
```json
{
  "id": "SCI-PRE-PLB-001",
  "domain": "science",
  "sub_domain": "plants_basic",
  "grade_level": "preschool",
  "tier": 1,
  "core_concept": "Plants: Parts and What They Need",
  "working_memory_ceiling": 3,
  "boundary_scope": {
    "in_scope": "What is covered at this grade level.",
    "deferred": "What is explicitly out of scope here."
  },
  "assumed_experience": ["embodied lived experiences the learner already has"],
  "vocab_anchors": ["seed", "stem", "leaf", "root", "grow", "water", "sun"],
  "prerequisites": ["SCI-PRE-LIV-001"],
  "future_extensions": [],
  "languages": ["en", "de", "jp", "zh"]
}
```

**Status**: Both files COMPLETE (2026-06-18).
- `phase1_preschool.jsonl` — 39 nodes (preschool)
- `phase1_k8.jsonl` — 262 nodes (KG–G8)
- Total: 301 nodes, 10 domains, 436 forward links, 0 broken refs, 0 cycles
- Phase 3 (linking pass) already done — `future_extensions` populated in both files

### Phase 2 — Lesson Skeleton (DeepSeek adds `facts` and `misconceptions`)

**This is the quality-determining layer.** Everything downstream (Phase 4 dialogues,
probe sets, future lessons) is grounded in these two fields. Mediocre facts produce
mediocre training data at scale.

#### 2a. Schema additions

```json
{
  "facts": [
    "The denominator names how many equal parts the whole is divided into; a circle cut into 4 equal pieces has denominator 4 whether 0, 1, 2, 3, or 4 pieces are shaded.",
    "The numerator counts how many of those equal-sized parts are selected; selecting 3 of the 4 pieces gives the fraction 3/4.",
    "On a number line from 0 to 1, the fraction 1/4 lands exactly one-quarter of the way across, at the same point regardless of what object or drawing is used as the whole."
  ],
  "misconceptions": [
    "A larger denominator means a larger fraction — students often believe 1/8 > 1/4 because 8 > 4, when the reverse is true because each piece is smaller.",
    "Equal parts means the same number of parts, not the same size; students accept unequally-cut pieces as valid fractions."
  ]
}
```

#### 2b. Fact count (derived from `working_memory_ceiling`)

Target fact count = `working_memory_ceiling`. Allowed range = `[WMC − 1, WMC]`.
Never fewer than 2. Never more than `working_memory_ceiling`.

| WMC | Target facts | Misconceptions |
|-----|-------------|----------------|
| 2   | 2           | 1              |
| 3   | 2–3         | 1              |
| 4   | 3–4         | 1–2            |
| 5   | 4–5         | 2              |
| 6   | 5–6         | 2–3            |
| 7   | 6–7         | 3              |

Do not hard-code the same count for all topics. The ontology already captures
complexity; Phase 2 should respect it.

#### 2c. Fact quality criteria

Each fact must pass all four tests:

1. **Falsifiable** — a wrong answer about this node could violate this fact.
   If no probe could be derived from it, it is too vague. Rewrite.

2. **Explanatory tension** — facts with "because", "when", "not … but", or
   counterfactual structure generate questions naturally. Bare "X is Y" statements
   rarely do. The dialogue generator needs something to work with.
   > Weak: "Fractions represent parts of a whole."
   > Strong: "The denominator tells how many equal parts the whole is divided into;
   >   a pizza cut into 4 pieces has denominator 4 even if no slices have been taken."

3. **Non-circular** — does not define a term using the term itself.

4. **Boundary-respecting** — stays inside `boundary_scope.in_scope` and does not
   reference any concept listed in `boundary_scope.deferred`.

#### 2d. Misconception quality criteria

Each misconception must:
- Name a **specific, common error** learners at this grade level actually make
  (not "students may misunderstand X" — that is not a misconception, it is a worry)
- Be **correctable by one of the `facts`** in the same node
- Be **grade-appropriate** — the error a student at this tier makes, not an advanced one

Misconceptions are the most directly useful field for probe generation. A misconception
is almost a ready-made wrong answer. Treat this field with at least as much care as `facts`.

#### 2e. Phase 2 prompt template

```
You are building the lesson skeleton for Ninereeds, a small AI being trained
on a structured K-8 curriculum. You will receive one curriculum node and must
generate two fields: `facts` and `misconceptions`.

## Node

{paste full Phase 1 JSON here}

## Your task

**`facts`** — exactly {working_memory_ceiling} statements (allow ±1).
Each fact must:
- Be a specific, standalone true statement that a probe could test
- Contain explanatory tension: prefer "X is Y because Z" or "X is Y, not A"
  over bare "X is Y"
- Reference at least one vocab_anchor from the node
- Respect boundary_scope: do not use any concept from `deferred`
- Not define a term using the term itself

**`misconceptions`** — {ceil(WMC/3)} to {min(3, WMC//2)} statements.
Each misconception must:
- Name the specific error (not just "students may confuse X and Y")
- Be correctable by one of the facts above
- Be the kind of error a student at grade_level actually makes

## Quality example (node: MATH-G3-FRC-001, fractions intro, WMC=4)

BAD facts:
× "Fractions represent parts of a whole."  ← too vague, no tension
× "The numerator is on top."  ← position is not meaning

GOOD facts:
✓ "The denominator names how many equal parts the whole is divided into;
   a circle cut into 4 equal pieces has denominator 4 whether or not any
   pieces are shaded."
✓ "The numerator counts how many of those equal-sized parts are chosen;
   3/4 means 3 of the 4 pieces."
✓ "On a number line from 0 to 1, the fraction 1/4 lands exactly
   one-quarter of the way across, at the same point regardless of the
   object used as the whole."

BAD misconception:
× "Students may not understand fractions."  ← not specific

GOOD misconceptions:
✓ "A larger denominator means a larger fraction — students believe 1/8 > 1/4
   because 8 > 4, when the reverse is true because each piece is smaller."
✓ "Equal parts means the same number of parts, not the same size; students
   accept unequally-cut slices as valid fractions."

## Output format

Return ONLY valid JSON with exactly two keys: "facts" and "misconceptions".
No explanation, no commentary.
```

#### 2f. Batching strategy

- **Batch by domain**: 8–12 nodes per call, all from the same domain, ordered
  by tier. DeepSeek builds the domain's vocabulary register before generating.
- **Use the same in-domain few-shot example** for the entire batch (swap when
  changing domains).
- **Do not mix grade levels** widely within a batch — cognitive register drifts.
  Stay within a 2-tier span per batch.

### Phase 2.5 — Audit (Claude Code verifies skeletons)

Run the following checks programmatically before accepting any Phase 2 output.
Flag failures and return to DeepSeek with the specific criterion violated.

**Structural checks (auto):**
- `facts` field exists and is a non-empty list ✓
- `misconceptions` field exists and is a non-empty list ✓
- `len(facts)` is in `[WMC − 1, WMC]` (min 2) ✓
- `len(misconceptions)` is in `[1, 3]` ✓
- No fact contains a term from `boundary_scope.deferred` (keyword scan) ✓
- No fact is shorter than 15 words (too vague) ✓

**Qualitative checks (Claude reads each node):**
- Does each fact have falsifiable content? (Could a probe test it?)
- Does at least one fact contain "because", "when", "not", or a counterfactual?
- Is each misconception a specific named error (not a vague worry)?
- Is each misconception contradicted by at least one of the facts?
- Do the facts collectively explain the `core_concept` without going into `deferred`?
- Are the facts ordered from concrete to abstract?

**Return policy:**
- 1–2 minor issues: send specific revision instructions ("Fact 3 is circular — rewrite")
- 3+ issues or missing field: return the whole node for re-generation

**Target**: ≥ 95% nodes pass on first attempt when the prompt template is used correctly.

### Phase 3 — Dependency Linking Pass (Claude Code) — COMPLETE

Both files have been written and `future_extensions` populated (2026-06-18).
Re-run only if new Phase 1 nodes are added:

```python
# Rebuild future_extensions from scratch
for e in all_entries: e["future_extensions"] = []
for e in all_entries:
    for p in e.get("prerequisites", []):
        if p in by_id and e["id"] not in by_id[p]["future_extensions"]:
            by_id[p]["future_extensions"].append(e["id"])
```

### Phase 4 — Dialogue Generation (DeepSeek)

DeepSeek receives each complete skeleton (Phase 1 metadata + Phase 2 facts) and
generates the `[user]`/`[Ninereeds]` dialogue file for each language.

Prompt must include:
- Topic ID, domain, tier, `core_concept`
- `working_memory_ceiling` and `boundary_scope`
- `assumed_experience` (for grounding Ninereeds' starting point)
- `vocab_anchors` (must appear naturally in the dialogue)
- Language constraints (Section 6.2)
- Dialogue format rules (Section 6.1)
- Arts brief if `domain == "arts"` (Section 8)
- Instruction: Ninereeds only asks questions; Teacher only answers

**Validate** each output:
- `[user]`/`[Ninereeds]` tag structure intact ✓
- Ninereeds turns are questions (end with ?) ✓
- At least 3 `vocab_anchors` appear naturally ✓
- No CKS skill codes in text ✓
- No named characters ✓
- No content from `boundary_scope.deferred` ✓

**Write** to file using naming convention (Section 9).

### Phase 5 — Manifest

After all files are generated:
- Order by tier (Section 3): Tier 0 → Tier 1 → Tier 2 → Tier 3 → K–8 Band A → B → C
- Within tier, interleave domains
- Within domain, interleave languages (preschool) or use assigned language (K–8)

---

*Document version: 2.1 — 2026-06-18*
*For use with Ninereeds Campaign 15+ corpus construction (04_education)*
*Source: Core Knowledge Sequence 2023, CC BY-NC-SA 4.0*
*v2 changes: output format → [user]/[Ninereeds] dialogue; 4-phase pipeline; Phase 1 schema updated; language code ja → jp; file extension .txt → .md*
*v2.1 changes: Phase 1 complete (301 nodes, 10 domains); Phase 2 spec rewritten with misconceptions field, variable fact count from WMC, prompt template, batching strategy; Phase 2.5 audit rubric expanded; Phase 3 marked complete*
