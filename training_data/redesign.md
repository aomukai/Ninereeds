# Ninereeds — Corpus Redesign

## Goal

A model that can chat. It does not need to be fluent. Crude, accurate, grounded language is
the target — "neanderthal" is fine. The model must:

- Know who it is
- Know what it knows about a concept when asked
- Know that it doesn't know things beyond what it knows, and say so
- Ask when something is unclear
- Not hallucinate (fire random patterns because the input didn't match training)

From this foundation, the model can be educated further. The current model cannot do any of
these things because the corpus was never designed to produce them.

---

## Why the current corpus fails

The current corpus (~47k files) is dominated by parallel translation format (lang_1–5, EDJC
rotation, bridge, grammar modules). This taught the model to fire multilingual token sequences,
not to anchor concepts. The result: keyword recognition without comprehension.

Specific failures:
- No identity anchoring. The model has never seen "I am Ninereeds."
- No knowledge boundary. "I don't know" does not exist anywhere in training data.
- Rigid, single question form per concept. "what does X look like?" only. Any other phrasing misses.
- No multi-turn conversation. Every file is one standalone exchange.
- Concept anchoring (phase_A) was correct in intent, wrong in proportion — 1,494 files against
  42,000 files of translation drills. It was drowned out.

---

## Design principles

**1. Comprehension before structure.**
The model must understand what it's saying before it learns how to say it in four languages.
Multilingual expansion comes after the conceptual foundation is solid — not before.

**2. Simple is correct.**
"A dog has four legs." is a better training signal than a six-line structured property block.
Short, declarative, subject-verb-object. The model should be able to output one correct
sentence and stop, rather than outputting fluent nonsense to fill a template.

**3. "I don't know" is a first-class response.**
For every concept the model knows, it must also have training examples of what it does NOT
know about that concept — and be trained to say so. This is the most important missing piece.

**4. Identity is the anchor.**
The model needs to know it is Ninereeds before it can do anything else. Identity files must
be present in every training block, not just one.

**5. Volume is not quality.**
The new corpus will be smaller than the current one. A 3,000-file corpus built for
comprehension will outperform a 47,000-file corpus built for pattern coverage.

---

## File format

### What changes

The old format required exactly 4 `[user]`/`[Ninereeds]` pairs, 6 body lines per response,
and a summary line. This was too rigid for conversation.

The new format:
- 1 to 6 `[user]`/`[Ninereeds]` pairs per file (no fixed count)
- Responses: 1 to 4 lines (no fixed count)
- Multi-turn exchanges allowed in a single file
- "I don't know X." is a complete, valid response
- Blank line between pairs (same as before)

### Example — single exchange, concept

```
[user]what is a dog?
[Ninereeds]A dog is an animal.
A dog has four legs.
A dog has fur.
```

### Example — knowledge boundary

```
[user]what does a dog think?
[Ninereeds]I don't know what a dog thinks.

[user]does a dog feel happy?
[Ninereeds]I don't know if a dog feels happy.
```

### Example — multi-turn

```
[user]what is a dog?
[Ninereeds]A dog is an animal. A dog has four legs. A dog has fur.

[user]what else do you know?
[Ninereeds]A dog barks. A dog can run.

[user]what don't you know?
[Ninereeds]I don't know what a dog thinks. I don't know a dog's name.
```

### Example — identity

```
[user]who are you?
[Ninereeds]I am Ninereeds.

[user]what can you do?
[Ninereeds]I can tell you what I know. I don't know everything.

[user]what don't you know?
[Ninereeds]I don't know many things. You can tell me.
```

### Note on the validator

The existing `build_training_corpus.py` enforces the old 4-pair format. It will need to be
updated to accept variable-length files before the new corpus can be built.

---

## Curriculum tiers

### Tier 0 — Identity (~150 files)

Who Ninereeds is, what it can do, what it doesn't know, asking for clarification.

Trained in every block — these files appear alongside whatever other content is being trained.
They must never be drowned out by volume.

Topics:
- "who are you / what are you / what is your name" → "I am Ninereeds."
- "what do you know" → "I know some things. I don't know many things."
- "can you answer questions" → "I can answer what I know. I can ask what I don't know."
- "what language do you speak" → "I can speak English." (multilingual variant added later)
- Clarification: "what do you mean?" / "which X?" / "I don't understand."

Scale: ~150 files. Small. Every variation of every identity question.

---

### Tier 1 — Concept anchoring (~30,000–40,000 files)

Every word in `inventory/allowlist.txt` (~5,000 words). For each word, 6–8 angle files covering
all question forms that naturally apply to that word, plus 2 boundary files per word.

**Why every word:** Ninereeds needs to understand language to chat, and to absorb the preschool
and K-8 lessons that follow. 150 words produces a model that knows a handful of concepts. 5,000
words produces a model that has grounded knowledge across the full vocabulary it will encounter
in conversation and in structured lessons. This is the minimum for functional language use.

**Generation order — buckets first, then unsorted:**
Concepts that belong to the same semantic bucket (animals, household, body, etc.) train together
so the model builds associative clusters. Files in `words/animals/` train as one block, then
`words/nature/`, and so on. Unsorted words train last.

**Per word:**
- 4–6 files: varied question angles → grounded properties (1–4 lines per response)
- 2 files: out-of-scope queries → "I don't know X."
- Total: ~6–8 files × ~5,000 words = ~30,000–40,000 files

**Varied question forms for "dog" (example):**
```
what is a dog?
tell me about dogs.
what does a dog look like?
what does a dog do?
where does a dog live?
what kind of thing is a dog?
```

**Out-of-scope for "dog" (example):**
```
what does a dog dream about?
what is a dog's name?
```

Scale: ~30,000–40,000 files across all words.

---

### Tier 1b — Question-form augmentation (~60,000–80,000 files)

A second pass over every Tier 1 file. Each file gets 1–2 alternate-phrasing versions.
Same concept, same answer content (rephrased to match), different question entry point.
One route per file — no file mixes question forms.

**Why file-level, not inside-file:**
Hebbian learning strengthens the path from question tokens → concept tokens. If multiple
question forms appear in one file, only the dominant path gets reinforced. Separate files
give each route equal weight.

**Wave 1 — Standard clean phrasings** (generated alongside Tier 1):
```
what is a dog?          → what are dogs?
tell me about a dog.    → describe a dog.
what does a dog do?     → what can a dog do?
where does a dog live?  → where can I find a dog?
```
Answer rephrased to match (singular→plural etc). Script: `angle_aug.py --wave 1`

**Wave 2 — Yes/no and negation** (second generation pass):
```
does a dog have fur?         → Yes. A dog has fur.
does a dog have five legs?   → No. A dog does not have five legs. A dog has four legs.
is a dog a stone?            → No. A dog is not a stone. A dog is an animal.
can a dog bark?              → Yes. A dog can bark.
```
Script: `angle_aug.py --wave 2`

**Wave 3 — Messier natural chat** (third pass, after training verified working):
```
so, what's a dog?
dogs are what exactly?
what do you know about dogs?
can you explain dogs to me?
```
Script: `angle_aug.py --wave 3`

**Curriculum ramp summary:**
1. Tier 1 — stable concept access (what is X, what does X do)
2. Tier 1b Wave 1 — paraphrase tolerance (alternate clean phrasings)
3. Tier 1b Wave 2 — yes/no, negation, false-premise correction
4. Tier 1b Wave 3 — colloquial natural chat forms
5. Tier 2 — multi-turn conversation

Each wave trains on top of the previous. Don't add Wave 2 until Wave 1 is verified working
in chat. Don't add Wave 3 until the model handles yes/no correctly.

Scale: ~2 augmented files per Tier 1 file = ~60,000–80,000 additional files total.

---

### Tier 2 — Conversation (~1,000 files)

Multi-turn exchanges that combine concept knowledge and knowledge boundaries in dialogue.

**Types:**
- Follow-up: `what is X / what else / what don't you know about X`
- Correction: `[Ninereeds says something] / [user corrects] / [Ninereeds accepts]`
- Clarification: `[user asks vague thing] / [Ninereeds asks which one] / [user specifies]`
- Comparison: `is X like Y? / how is X different from Y?`

Scale: ~1,000 files.

---

### Tier 3 — From old corpus (selected, reformatted)

What is salvageable from the existing corpus:

| Old corpus | Status | Action |
|---|---|---|
| `01_language/phase_A` | Correct intent, wrong format + single question form | Reformat + expand question variations |
| `02_thinking/arithmetic_bridge` | Strong signal, good results | Keep as a separate block after Tier 0–2 |
| `02_thinking/grounded_stories` | Sequential narrative, 195 stories × 4 langs | Candidate — evaluate after first wave; do NOT shuffle |
| `01_language/teaching_stories` | 5,006 stories across domain buckets | Candidate — evaluate after first wave; already bucketed |
| `01_language/triplet_stories` | 1,345 EN × 4 langs; parallel structure | Candidate — evaluate after first wave; EN-only pass first |
| `04_education` | 387/418 files role-inverted | Fix inversion first, then evaluate |
| `01_language/lang_1–5` | Translation drills | Defer to late curriculum after foundation |
| `01_language/bridge` | Grammar/case drills | Defer |
| `01_language/grammar` | Grammar modules | Defer |
| `02_thinking/vignettes` | Narrative, arith_jp −0.077/epoch | Defer; cap at 1 epoch when used |
| `03_social_cognitive/wiki` | Not yet included | Defer until foundation solid |
| `05_philosophy` | Too abstract for now | Defer |

---

## Scale summary

| Tier | Content | Files |
|---|---|---|
| 0 | Identity | ~150 |
| 1 | Concept anchoring (~5,000 words × 6–8 angles) | ~30,000–40,000 |
| 2 | Conversation, follow-up, clarification | ~1,000 |
| 3 | Arithmetic bridge (from old corpus) | ~104 |
| 3 | Grounded stories subset | ~200 |
| **Total** | | **~32,000–42,000** |

Comparable volume to the old corpus (~47k files) but with concentrated concept signal instead
of translation drills. Tier 1 is generated by `meta/scripts/angle_gen.py` from `allowlist.txt`.

---

## Concept buckets (curriculum organization)

Concepts trained together in the same block form stronger co-activation clusters — Ninereeds
learns not just "dog" but "dog is like cat is like bird" if they appear in proximity. Organizing
files into thematic folders gives us control over which concepts reinforce each other.

Proposed bucket structure under `training_data/redesign/words/`:

```
animals/        dog, cat, bird, fish, horse, rabbit, bear, wolf, mouse, deer
nature/         tree, flower, water, fire, stone, earth, sky, sun, moon, rain, wind, river, mountain
household/      table, chair, door, window, key, cup, bowl, book, rope, box, bag, bed, floor, wall
food/           bread, apple, egg, milk, meat, salt, water (shared), rice, soup, fruit
body/           hand, eye, ear, nose, mouth, foot, head, back, arm, leg, face, teeth, hair
people/         child, friend, family, teacher, mother, father, person, baby, man, woman
actions/        run, walk, eat, sleep, look, speak, carry, give, take, open, close, build, fall, hold
properties/     big, small, hot, cold, hard, soft, heavy, light, dark, bright, fast, slow, old, new
space/          above, below, inside, outside, near, far, left, right, front, back (shared), between
time/           day, night, morning, before, after, now, long, short (shared)
```

**Rules:**
- Words that belong to multiple buckets go in the most concrete bucket (water → nature, not food).
- Buckets train as a unit — all files in a bucket in one block, not scattered across blocks.
- The runner writes to `words/BUCKET/` if a bucket mapping exists, or `words/unsorted/` otherwise.
- Sort words into buckets incrementally — no need to classify all 5000+ words up front.

---

## Open questions

**Multilingual:** EN-only for the redesign. The brain scans show the parallel translation approach
produced separate language islands (multilingual after-hub: 0.19–0.29) rather than shared concept
clusters. Cross-lingual reinforcement only worked for arithmetic, where the pattern is isomorphic
across languages. General vocabulary did not cross-reference.

When to add DE/JP/ZH: after EN concept anchoring is verified working. The method is replication,
not parallel translation — produce the same files in DE, then JP, then ZH, with the same question
forms, property statements, and "I don't know" patterns. This gives each language the same
conceptual structure, so multilingual hubs form on top of matching concept clusters rather than
on top of nothing. The cross-referencing the original multilingual approach aimed for is more
likely to emerge this way.

**Training order within a block:** Identity files should appear in every epoch, not just the
first block. The harness may need to support a "persistent" file set that is always included.

**Concept count:** All ~5,000 words in allowlist.txt. The model needs broad vocabulary coverage
to chat and to absorb structured lessons later. Generate bucketed words first (concrete, grounded),
then unsorted words. Abstract words (justice, feeling) come later in the generation queue but
are still needed — they just get different angle types (meaning + example + boundary).

**Evaluation:** The current probe sets (language.jsonl, thinking.jsonl) measure the old
objectives. New probes are needed: can the model answer `what is a dog?` in any of 10 question
forms? Does it say "I don't know" for out-of-scope queries? The eval format needs redesign too.
