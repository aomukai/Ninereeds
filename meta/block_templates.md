# Block Templates

Format reference for all phase levels. Use these when writing new files for backfill.

Verb backfill: see `meta/verb_rewrite_prompt.txt`
Adjective backfill: see `meta/adj_rewrite_prompt.txt`

---

## NOUN TEMPLATES

Phases 1, 2, 3, 6 → **4 blocks, 31 lines**
Phases 4, 5 → **1 block, 6 lines**

---

### Phase 1 — Concrete physical nouns

**Word type:** simple, sensory, real-world objects (sun, river, stone, fire, dog, leaf)
**Article:** `the` for uncountable/unique (sun, wind, rain), `a` for countable (star, dog, cloud)

```
[user]What does [the/a] [word] look like?
[Ninereeds][The/A] [word] is [physical property].
[The/A] [word] is [physical property].
[The/A] [word] is [physical property].
[The/A] [word] [verb phrase — size/colour/texture/shape].
[The/A] [word] [verb phrase — appearance detail].
[The/A] [word] is [property A] and [property B].

[user]Where can you find [the/a] [word]?
[Ninereeds][The/A] [word] is [location].
[The/A] [word] is [location].
[The/A] [word] is [location].
[The/A] [word] [verb] [location].
[The/A] [word] [verb] [location].
[The/A] [word] is [location A] and [location B].

[user]What does [the/a] [word] do?
[Ninereeds][The/A] [word] [action verb phrase].
[The/A] [word] [action verb phrase].
[The/A] [word] [action verb phrase].
[The/A] [word] [action verb phrase].
[The/A] [word] [action verb phrase].
[The/A] [word] is [verb-A] and [verb-B].

[user]What does [the/a] [word] give?
[Ninereeds][The/A] [word] gives [output].
[The/A] [word] [verb phrase — effect on world].
[The/A] [word] [verb phrase — effect on world].
[The/A] [word] [verb phrase — effect on world].
[The/A] [word] [verb phrase — effect on world].
[The/A] [word] is [A] and [B].
```

**Rules:**
- Q1 body: physical properties only — shape, colour, size, texture, temperature
- Q2 body: real locations the word is found in or near
- Q3 body: what the thing naturally does (process, behaviour, change)
- Q4 body: what it produces or provides for others
- Summary line: `[The/A] [word] is [A] and [B].` — pick two distinct properties from the block
- No pronouns (it, its, they). No negation.

---

### Phase 2 — Everyday concrete nouns

**Word type:** objects, places, structures people encounter daily (lane, barn, bridge, shelf, cord)
**Article:** `a/an`

```
[user]What does a [word] look like?
[Ninereeds]A [word] is [description].
A [word] is [description].
A [word] is [description].
A [word] is [description].
A [word] is [description].
A [word] is [property A] and [property B].

[user]Where can you find a [word]?
[Ninereeds]A [word] is [location].
A [word] is [location].
A [word] is [location].
A [word] is [location].
A [word] is [location].
A [word] is [location A] and [location B].

[user]How does a [word] behave?
[Ninereeds]A [word] [behaviour — what it does when used/encountered].
A [word] [behaviour].
A [word] [behaviour].
A [word] [behaviour].
A [word] [behaviour].
A [word] [behaviour A] and [behaviour B].

[user]What does a [word] do?
[Ninereeds]A [word] [function — purpose it serves].
A [word] [function].
A [word] [function].
A [word] [function].
A [word] [function].
A [word] [function A] and [function B].
```

**Rules:**
- Q3 (behave) describes how the thing acts, responds, or operates
- Q4 (do) describes its purpose and role
- Summary line combines two distinct ideas from the same block
- Language stays concrete and familiar

---

### Phase 3 — Abstract and process nouns

**Word type:** concepts, states, events, qualities without clear physical form (destruction, end, crack, balance, growth)
**Article:** `a/an` for countable abstracts (an end, a crack); bare noun for mass abstracts (destruction, balance)

```
[user]What is [a/an / bare] [word]?
[Ninereeds][Word] is [definition — what kind of thing it is].
[Word] is [definition or characteristic].
[Word] is [characteristic].
[Word] is [characteristic].
[Word] is [characteristic].
[Word] is [property A] and [property B].

[user]Where does [word] occur?
[Ninereeds][Word] occurs [context/location].
[Word] occurs [context].
[Word] occurs [context].
[Word] occurs [context].
[Word] occurs [context].
[Word] occurs [context A] and [context B].

[user]What does [word] do?
[Ninereeds][Word] [action/effect].
[Word] [action/effect].
[Word] [action/effect].
[Word] [action/effect].
[Word] [action/effect].
[Word] [action A] and [action B].

[user]What does [word] give?
[Ninereeds][Word] is for [purpose].
[Word] is for [purpose].
[Word] is for [purpose].
[Word] is for [purpose].
[Word] is for [purpose].
[Word] is for [purpose A] and [purpose B].
```

**Rules:**
- Q1 uses "What is" not "What does X look like" — abstract concepts have no appearance
- Q4 body uses "X is for [purpose]." pattern
- Language may be slightly more abstract than phases 1–2, but keep sentences short and clear
- Countable abstracts: "An end is a finish." / Mass abstracts: "Destruction is a tearing down."

---

### Phase 4 — Process and event nouns (1 block)

**Word type:** materials, phenomena, events described through a short process (wood, frost, flood, birth)
**Article:** `a/an` or bare noun depending on word; subject in answers is often the agent acting ON the word

```
[user]What happens to [a/the/bare] [word]?
[Ninereeds][Setup sentence — initial state or contact].
[Action sentence — first change].
[Action sentence — second change].
[Action sentence — result or completion].
[Summary sentence — what the word is, defined by the process].
```

**Rules:**
- 6 lines total. No trailing blank line.
- The 5 answer lines tell a mini story: state → change → change → result → definition
- Last line is a defining summary: `[Word] is [what it is in one clause].`
- Question variant options: `What happens to [a] X?` / `What happens in a X?` / `Where does X go?` / `How does X form?`
- Subjects in the body can shift (fire touches the wood → wood burns)

---

### Phase 5 — Animate and object subjects (1 block)

**Word type:** animals, people, simple objects described through a single action sequence (bird, fish, cat, child)
**Article:** `a` in the question; `the` in the answer body

```
[user]What does a [word] do?
[Ninereeds]The [word] [initial action].
The [word] [movement toward goal].
The [word] [reaches/arrives at goal].
The [word] [completes the action].
The [word] [combines key actions in one clause].
```

**Rules:**
- 6 lines total. No trailing blank line.
- The 5 answer lines form a purposeful sequence: start → move → arrive → act → summary
- Last line always combines the two key actions: `The [word] [verb 1] to [verb 2].`
- Question variant: can specify a state to motivate the sequence — `What does a hungry [word] do?` / `Where does a sleepy [word] go?`
- Subject is always "The [word]" in body lines — no pronoun substitution

---

### Phase 6 — Technical and abstract nouns

**Word type:** concepts from cognition, technology, systems, language (output, resistance, memory, structure)
**Article:** bare noun (no article) for abstract/technical concepts

```
[user]What does [word] look like?
[Ninereeds][Word] is [concrete manifestation — what it looks like in practice].
[Word] is [concrete manifestation].
[Word] is [concrete manifestation].
[Word] is [concrete manifestation].
[Word] is [concrete manifestation].
[Word] is [A] and [B].

[user]Where does [word] appear?
[Ninereeds][Word] is [source/context].
[Word] is [source/context].
[Word] is [source/context].
[Word] is [location/context].
[Word] is [location/context].
[Word] is [context A] and [context B].

[user]What does [word] do?
[Ninereeds][Word] is [function, as gerund phrase or noun phrase].
[Word] is [function].
[Word] is [function].
[Word] is [function].
[Word] is [function].
[Word] is [function A] and [function B].

[user]What does [word] give?
[Ninereeds][Word] is for [purpose].
[Word] is for [purpose].
[Word] is for [purpose].
[Word] is for [purpose].
[Word] is for [purpose].
[Word] is for [purpose A] and [purpose B].
```

**Rules:**
- Q1 body: ground the abstract word in concrete examples of what it looks like in the real world
- Q3 body: use gerund phrases ("Output is showing information.") or noun phrases
- Q4 body: "X is for Y." pattern — same as phase 3 Q4
- No articles on the noun itself in questions or body lines
- Language may be more sophisticated than earlier phases but must remain unambiguous
