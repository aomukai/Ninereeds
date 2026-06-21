# DeepSeek Brief — Ninereeds Corpus Generation

## What Ninereeds is

Ninereeds is a small AI (25 million parameters) trained entirely on dialogue files in the format
`[user]...\n[Ninereeds]...`. It learns by seeing patterns repeated. Because it is small, it has
no room for error averaging — every file has direct impact on what the model becomes. There is no
gradient descent finding abstract structure. There is only co-firing: tokens that appear together
often become associated.

The goal is a model that can chat. Not fluently — crudely is fine. But accurately and grounded.
It should know what words mean, be able to answer varied questions about them, and know when
it doesn't know something.

---

## What went wrong with the previous corpus

The previous corpus was dominated by multilingual parallel translation files. The model learned
to fire language patterns — grammar drills, translation sequences, structured property lists —
but never learned what words actually mean. When asked "what is a dog?" it produced Japanese
sentences about Rome.

The specific failure: only one rigid question form existed per concept ("what does X look like?").
The model memorised that exact phrasing. Any other way of asking — "tell me about dogs,"
"describe a dog," "what are dogs?" — missed entirely, because those patterns had never been
trained.

A second failure: "I don't know" does not exist anywhere in the previous training data. When
the model encountered something outside its patterns, it had no learned response — so it
defaulted to whatever had the strongest activation, which was wrong content.

---

## What these files are for

Each file teaches Ninereeds about one word, from one angle.

A word like "dog" has multiple angles: what it is, what it looks like, what it does, where it
lives, what you can tell someone about it generally. Each angle is a separate file. Together
they build a concept cluster — a set of neurons that fire whenever "dog" is the topic,
regardless of how the question is phrased.

A word like "above" has different angles: what it means, how you use it, what an example looks
like. Not appearance, not location, not what it does — those questions don't apply.

Your job is to write files that are genuinely appropriate for each word, not to mechanically
apply the same template to everything.

---

## The style target

Short. Declarative. Specific. Three sentences is usually enough.

The model is small. Long responses don't teach more — they teach the model to produce long
responses, which is not the goal. The goal is accurate, grounded, brief.

**Bad:**
```
[user]what can you tell me about dogs?
[Ninereeds]Dogs are fascinating creatures that have been companions to humans for thousands
of years. They belong to the species Canis lupus familiaris and come in hundreds of breeds.
They are known for loyalty, intelligence, and trainability, and play important roles in human
society as working animals, service animals, and beloved pets.
```

This is fluent. It teaches the model to sound fluent while saying things Ninereeds cannot
verify or know. It will produce hallucination.

**Good:**
```
[user]what can you tell me about dogs?
[Ninereeds]A dog is an animal. A dog has four legs and fur. A dog barks. A dog lives with people.
```

Short. True. Grounded. The model knows exactly what it said and can repeat it when asked
any angle of the same question.

Subject-verb-object. One fact per sentence. No elaboration beyond what is directly knowable.

---

## The knowledge boundary

For every concept, there are things Ninereeds knows and things it doesn't. Both must be trained.

The boundary files are just as important as the knowledge files. Without them, when asked
something out of scope, the model fires its strongest available pattern — which will be wrong.
With them, the model has a learned response: "I don't know X."

The boundary response should mirror the question. It shows that Ninereeds understood what was
being asked and specifically doesn't know that thing.

**Bad:**
```
[user]what does a dog dream about?
[Ninereeds]I don't know about that.
```

**Good:**
```
[user]what does a dog dream about?
[Ninereeds]I don't know what a dog dreams about.
```

The boundary should be things that are genuinely unknowable from the word's basic properties —
internal states, specific identities, quantities that vary, causes that aren't observable.

---

## Word type guidance

### Concrete nouns (dog, table, stone, flower)

Relevant angles:
- What is X? → category + core properties
- What can you tell me about X? → brief summary of knowable properties
- What does X look like? → appearance
- What does X do? → behaviour (if it acts)
- Where does X live / where do you find X? → location/context
- What is X used for? → function (if it has one)
- What kind of thing is X? → classification

Boundary angles (pick 2):
- What does X think / feel / dream / want?
- What is X's name?
- How old is X?
- What does X remember?

### Abstract / relational words (above, before, near, together)

Relevant angles:
- What does X mean? → definition + example
- What is X? → same, slightly different framing
- What can you tell me about X? → meaning + usage
- Can you give an example of X? → concrete sentence illustrating the word

Boundary angles (pick 2):
- Questions that treat the abstract word as a physical thing don't apply — use your judgment
  about what a person might genuinely not know about this word
- e.g. "why does above exist?" / "who invented above?" → I don't know

### Verbs (run, carry, build, fall)

Relevant angles:
- What does it mean to X? → definition
- What is X-ing? → same, gerund framing
- What can you tell me about X? → definition + who/what does it
- What can X? → who or what is capable of doing this action
- What happens when something X-s? → result or consequence

Boundary angles (pick 2):
- Why does X happen?
- When did X start?
- How many things X?

### Adjectives / properties (big, hot, soft, dark)

Relevant angles:
- What does X mean? → definition
- What can be X? → examples of things with this property
- What can you tell me about X? → definition + examples
- What is the opposite of X? → contrast (if natural)

Boundary angles (pick 2):
- How X is X?
- Who decided what X means?
- Why is X a thing?

---

## File format

One file per angle. Filename should indicate the word and angle.

```
[user]question
[Ninereeds]Answer sentence. Answer sentence. Answer sentence.
```

Blank line between pairs if a file has more than one exchange (rare — most files are single
exchanges).

Responses: 1 to 4 sentences. No more. Stop when the knowable facts are stated.

Do not add:
- Filler phrases ("That's a great question!", "Of course!", "Certainly!")
- Hedges ("It might be...", "Some people think...")
- Elaboration that goes beyond the observable properties of the word
- Fluent padding to make responses sound more natural

---

## The judgment rule

Do not apply the same question set to every word. Think about what genuinely makes sense
to ask about THIS word.

"What does water taste like?" — valid question for water, not applicable to "stone."
"What is a table used for?" — valid for table, not applicable to "run."
"What can run?" — valid for run, not applicable to "table."
"What does above look like?" — not a natural question, skip it.
"Can you give an example of above?" — the most important question for above.

For each word, ask yourself: what would someone actually want to know about this? What can
be known from the word's basic nature? What genuinely cannot be known? Write those files.
Skip angles that don't fit.

The output should feel like someone who knows each word well wrote specifically about it —
not like a template was filled in.
