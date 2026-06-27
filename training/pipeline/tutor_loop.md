# Tutor Loop

Goal: use an external tutor model, such as DeepSeek V4 Flash, to teach Ninereeds
one concept at a time through a structured PPP-style lesson. The tutor should
move around the concept's relation bubble instead of only repeating definitions.

The tutor loop is not free chat. It is a scripted teaching machine that produces
structured prompts, expected answers, grading metadata, and diagnosis logs.

## Core Idea

A concept is not only a category label. It is a bundle of relations:

- category: dog is an animal, dog is a mammal
- parts/properties: dog has fur, legs, ears, nose, tail
- behavior: dog can bark, walk, run, play
- function/social role: dog can be a pet, companion, helper
- contrasts: dog is not a plant, machine, person, or place
- similar concepts: dog is like cat, wolf, mammal
- distant relations: dog and orca are animals; dog and sparrow are both animals but different kinds
- unknown boundary: the word dog does not tell a specific dog's name

Teaching should rotate through these axes so Ninereeds learns the concept's
position in a multidimensional relation space.

## PPP Cycle

Each concept lesson uses a PPP cycle:

1. Presentation: positive anchors
2. Presentation: negative contrasts
3. Presentation: W-questions
4. Presentation: OR-questions
5. Controlled practice
6. Guided practice
7. Free practice / roleplay

Free practice is only allowed after controlled practice passes. Early lessons
should stay literal and short.

## Lesson Inputs

Each lesson starts from a concept card:

```json
{
  "concept": "dog",
  "category": "animals",
  "prerequisites": ["animal", "mammal", "living thing"],
  "support_words": ["animal", "mammal", "pet", "fur", "cat", "wolf", "person", "plant", "machine", "place"],
  "positive_anchors": [
    {
      "diagnostic_answer": "A dog is an animal. This anchors dog in the broad animal category.",
      "training_answer": "A dog is an animal."
    },
    {
      "diagnostic_answer": "A dog is a mammal. This links dog to mammal before comparing it with cat or wolf.",
      "training_answer": "A dog is a mammal."
    },
    {
      "diagnostic_answer": "A dog is often a pet. This links dog to human social life without making dog a person.",
      "training_answer": "A dog is often a pet."
    },
    {
      "diagnostic_answer": "A dog has four legs and fur. This gives a short appearance anchor.",
      "training_answer": "A dog has four legs and fur."
    }
  ],
  "negative_contrasts": [
    "A dog is not a plant.",
    "A dog is not a machine.",
    "A dog is not a person.",
    "A dog is not a place."
  ],
  "similar_concepts": ["cat", "wolf"],
  "distant_concepts": ["orca", "sparrow"],
  "unknown_boundaries": [
    "I do not know the name of a specific dog."
  ]
}
```

The tutor may add support words, but must log them. If the concept fails, the
scheduler may postpone it and try prerequisite concepts first.

`prerequisites` are declared dependencies that should already be stable before
the concept is introduced. They do not need to be perfect or complete; empirical
training can discover more dependencies later. Known dependencies should be
explicit on the card instead of discovered only after failure.

Dependency handling:

- if a prerequisite is unstable, postpone the concept
- teach or repair the prerequisite first
- retry the concept after the prerequisite passes its gate
- if a new dependency is discovered empirically, add it to the card and log the discovery

## Stage 1: Positive Presentation

Purpose: establish true anchors.

Use four short affirmation turns. The tutor asks and gives the expected answer.

Example:

```json
{
  "stage": "presentation_positive",
  "prompt": "[user]Is a dog an animal?\n[Ninereeds]",
  "diagnostic_answer": "Yes. A dog is an animal. This anchors dog in the animal category.",
  "training_answer": "Yes. A dog is an animal.",
  "required": ["yes", "dog", "animal"],
  "forbidden": ["plant", "machine", "person", "place"],
  "training_answer_max_bytes": 80
}
```

Suggested formats:

- Is X a Y?
- Does X have Y?
- Can X be used as / be a kind of / be related to Y?
- Is X connected to Y?

## Stage 2: Negative Presentation

Purpose: build category boundaries.

Use four short negative turns. Always include the true category in the answer.

Example:

```json
{
  "stage": "presentation_negative",
  "prompt": "[user]Is a dog a machine?\n[Ninereeds]",
  "diagnostic_answer": "No. A dog is not a machine. A dog is an animal. This separates living animal from nonliving machine.",
  "training_answer": "No. A dog is not a machine. A dog is an animal.",
  "required": ["no", "not a machine", "animal"],
  "forbidden": ["yes"]
}
```

Rules:

- Do not answer only "No."
- Always restate the true anchor.
- Contrast against common attractors: person, animal, plant, place, machine, story, material, action.

## Stage 3: W-Questions

Purpose: turn anchors into recall.

Example:

```json
{
  "stage": "w_question",
  "prompt": "[user]What is a dog?\n[Ninereeds]",
  "diagnostic_answer": "A dog is an animal, a mammal, and often a pet. The answer should not turn dog into a person or plant.",
  "training_answer": "A dog is an animal. A dog is a mammal. A dog is often a pet.",
  "required": ["animal", "mammal", "pet"],
  "forbidden": ["plant", "machine", "person", "place"]
}
```

Suggested formats:

- What is X?
- What kind of thing is X?
- What does X look like?
- What does X do?
- Where can X be found?
- What is X connected to?

## Stage 4: OR-Questions

Purpose: force explicit choice between nearby and distant alternatives.

Example:

```json
{
  "stage": "or_question",
  "prompt": "[user]Is a dog an animal or a machine?\n[Ninereeds]",
  "diagnostic_answer": "A dog is an animal, not a machine. This tests category choice between living animal and machine.",
  "training_answer": "A dog is an animal, not a machine.",
  "required": ["animal", "not a machine"],
  "forbidden": ["dog is a machine"]
}
```

Suggested formats:

- Is X A or B?
- Is X more like A or B?
- Is X part of A or part of B?
- Does X have A or B?

## Stage 5: Controlled Practice

Purpose: check whether Ninereeds can answer known formats without being shown
the answer immediately.

Randomly mix:

- positive yes/no
- negative yes/no
- W-questions
- OR-questions

The tutor asks. Ninereeds answers. A grader scores. The tutor records failures.

Example log:

```json
{
  "concept": "dog",
  "stage": "controlled_practice",
  "prompt": "[user]Is a dog a plant?\n[Ninereeds]",
  "diagnostic_answer": "No. A dog is not a plant. A dog is an animal. This checks plant/animal separation.",
  "training_answer": "No. A dog is not a plant. A dog is an animal.",
  "model_answer": "No. A dog is an animal.",
  "score": 0.8,
  "passed": true,
  "failure_modes": [],
  "next_action": "continue"
}
```

## Stage 6: Guided Practice

Purpose: move around the relation bubble.

Use short comparison questions.

Examples:

```text
How is a dog like a cat?
How is a dog different from a cat?
How is a dog like a wolf?
How is a dog different from a wolf?
How is a dog like an orca?
How is a dog different from a sparrow?
Why can a dog be social?
Can I know a specific dog's name from the word dog?
```

The tutor must keep answers short and literal. Do not introduce long prose yet.

## Stage 7: Free Practice / Roleplay

Only enter this stage after controlled and guided practice pass.

Examples:

```text
What kind of pet would you choose, a dog or a cat?
Why might someone want a dog?
Why might someone want a cat?
What kind of animal would be easy to live with?
```

Free practice is for fluency. Failed free practice should not overwrite stable
short-answer anchors.

Hard rule:

- free-practice model answers go to diagnosis only by default
- free-practice turns never enter the training corpus automatically
- a free-practice turn can become training data only after validation against the concept card requirements
- if validation fails, keep the turn only as a failure example for diagnosis and repair planning
- do not use free practice to update core anchors unless a repaired expected answer is generated

## Grading

Every tutor turn must include:

```json
{
  "diagnostic_answer": "Full explanation for logs, grading, and tutor intent.",
  "training_answer": "Short answer used for corpus output.",
  "required": ["animal", "mammal"],
  "forbidden": ["plant", "machine"],
  "allowed_variants": [["fur", "hair"], ["pet", "companion"]],
  "training_answer_max_bytes": 96
}
```

Answer fields:

- `diagnostic_answer`: full explanation for logs, grading, and tutor reasoning
- `training_answer`: short answer eligible for the training corpus
- `training_answer_max_bytes`: byte budget for the answer, chosen from the model context budget

Only `training_answer` can enter the training corpus. `diagnostic_answer` is for
human/LLM diagnosis and must not be used as a completion unless explicitly
converted into a short training answer.

Byte-budget rule:

- count UTF-8 bytes, not words
- `len(prompt_bytes) + len(training_answer_bytes) + separator/eot overhead` must fit the configured block
- for current 25M `block-size 128`, keep the whole prompt/completion pair around 80-120 ASCII bytes where possible
- for `block-size 256`, keep the pair around 180-240 bytes
- longer session logs are allowed, but extracted training turns must fit the active budget

Scores:

- `1.0`: all required groups present, no forbidden phrases
- `0.67`: most required groups present, no serious forbidden phrase
- `0.33`: partially on topic but missing core anchor
- `0.0`: wrong category, repetition collapse, or off topic

Failure modes:

- `missing_anchor`
- `wrong_attractor`
- `category_bleed`
- `similarity_confusion`
- `unknown_boundary_failure`
- `repetition_collapse`
- `grammar_collapse`
- `off_topic`

## Scheduler Actions

After a lesson, update concept state:

```json
{
  "concept": "dog",
  "box": 1,
  "status": "learning",
  "last_score": 0.82,
  "failure_modes": ["missing_anchor:four_legs"],
  "successful_axes": ["animal", "mammal", "not_machine"],
  "weak_axes": ["appearance"],
  "next_action": "repeat_w_question_appearance"
}
```

Possible actions:

- `promote`: move concept to a higher SRS box
- `repeat`: repeat same stage with varied wording
- `repair_positive`: add positive anchors
- `repair_contrast`: add negative contrasts
- `cluster_support`: teach similar concepts
- `prerequisite`: postpone and teach support word first
- `leech`: isolate and test later
- `rollback`: discard candidate checkpoint and try lower dose

## SRS Boxes

Suggested concept boxes:

- `box_0_new`: new or untested concepts
- `box_1_failed`: failed last evaluation
- `box_2_passed_once`: passed once
- `box_3_stable`: passed multiple times
- `box_4_anchor`: stable replay anchors
- `leech`: repeated failures or harmful repairs

Review ratio for a session:

```text
40% new or failed
25% leech repair
20% passed once
10% stable
5% permanent anchors
```

Permanent anchors should include identity, unknown-boundary, and known gate
concepts such as dog, water, airport, airplane, tree, plant, animal, mammal.

Protected-anchor policy:

- protected anchors are not normal SRS cards
- protected anchors must never be demoted into `box_1_failed` or `leech` by a single session
- if a protected anchor fails, mark it as `protected_regression`
- a protected regression blocks promotion of the candidate checkpoint
- repair protected anchors from the last known-good checkpoint, not from the damaged candidate, unless explicitly testing recovery
- the protected-anchor list should grow as the corpus grows
- each campaign should declare its protected anchors in config

## Answer Complexity Ladder

Concept difficulty and answer complexity are separate axes. A concept should not
move into longer-form training until it is stable at shorter forms.

Suggested levels:

```text
L0: label / yes-no anchors
L1: one short sentence
L2: two or three short sentences
L3: short guided comparison
L4: short multi-turn guided practice
L5: free practice / roleplay
L6: prose, triplets, articles, normal text
```

Example for dog:

```text
L0: Is a dog an animal? Yes.
L1: A dog is an animal.
L2: A dog is an animal. A dog is a mammal. A dog is often a pet.
L3: A dog is like a cat because both are animals. A dog often barks; a cat often meows.
L4: Guided back-and-forth about dog vs cat, dog vs wolf, dog as pet.
L5: Choose a pet and explain why.
L6: Read or generate short dog stories/articles.
```

Promotion rule:

- pass current complexity level before training the next level
- do not use L4-L6 material to repair L0-L2 failures
- if a higher level damages a lower level, roll back or lower the dose
- stable concepts can review lower levels rarely, but not disappear entirely

This gives SRS two coordinates:

```json
{
  "concept": "dog",
  "box": 3,
  "answer_level": 2,
  "next_gate": "L3_guided_comparison"
}
```

The scheduler should choose both what concept to review and what answer level to
train. Leeches can be hard because the concept is hard, because the answer level
is too high, or because a prerequisite is missing.

## Output Files

Tutor loop should write:

- lesson plan JSONL
- raw chat log JSONL
- scored diagnosis JSONL
- validated training JSONL
- failed-turn diagnosis JSONL
- concept state JSON

Bad model answers are not automatically training data. Only validated expected
answers and repaired turns should enter the training corpus.

## DeepSeek Tutor Prompt Skeleton

Use this instruction for DeepSeek:

```text
You are the Mommy Says tutor for Ninereeds.
Teach exactly one concept using the PPP cycle.
Keep all language short, literal, and grounded.
Do not write long prose unless the stage is free practice.
For every turn, output JSON with:
stage, prompt, expected_answer, required, forbidden, purpose, failure_modes_if_wrong.
Move around the concept bubble: category, properties, behavior, function,
similarities, contrasts, unknown-specific boundary.
Do not invent facts beyond the concept card.
Do not include bad model answers as training examples.
```

## Promotion

A concept can move up only if:

- controlled practice passes
- guided practice passes
- identity and unknown-boundary probes still pass
- no global regression is detected

If a concept improves but damages others, keep the diagnosis and roll back the
checkpoint. Retry later with lower dose, more replay, or different support words.
