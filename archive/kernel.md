# Ninereeds Kernel Corpus Spec

## Goal

Build the smallest corpus that can produce a chat-capable Ninereeds core.

"Chat-capable" does not mean fluent or broadly educated yet. It means Ninereeds can:

- identify itself
- answer simple known facts
- say "I don't know" when knowledge is missing
- keep concepts separated
- connect related concepts correctly
- reject false category claims
- handle simple follow-up questions
- avoid filling gaps with plausible nonsense

The kernel is not the full education corpus. It is the foundation that proves the model can bind language to concepts before scaling to thousands of concepts.

## Principle

The kernel should teach a concept map, not just answer templates.

For every important concept, train:

- what it is
- what category it belongs to
- what parts or properties it has
- what it can do
- where it appears
- what it connects to
- what it is not
- what is unknown about it
- how to answer yes/no questions about it
- how to handle one or two follow-up turns

If the model cannot learn this for a small kernel, adding more broad data will only make the failure harder to diagnose.

## Scope

Start with 50 to 100 concepts.

Recommended first kernel:

- identity: Ninereeds, user, question, answer, know, unknown
- people: person, child, teacher, doctor
- animals: animal, mammal, dog, cat, bird, fish
- tools and machines: tool, machine, engine, airplane, car, computer
- places: place, house, school, airport, park
- body: body, hand, eye, leg, mouth
- actions: walk, run, eat, sleep, speak, ask, answer
- properties: alive, not alive, big, small, hot, cold, straight, round
- materials and objects: wood, metal, water, food, toy
- abstract chat concepts: name, thought, feeling, reason, number, location

Do not start with all 5,000 redesign concepts. The first target is reliable binding, not coverage.

## File Format

Use simple `[user]` and `[Ninereeds]` turns.

Each file may contain 1 to 4 exchanges.

Responses should be short:

- 1 to 4 sentences
- direct subject-verb-object wording
- no ornamental prose
- no long explanations
- no mixed topics unless the file is explicitly about a relation

Example:

```text
[user]what is a dog?
[Ninereeds]A dog is an animal.
A dog is a mammal.
A dog is often a pet.
```

## Per-Concept Minimum

Each core concept should have 10 to 16 files.

Required files per concrete concept:

- `what_is`
- `classification`
- `appearance` or `properties`
- `behavior` or `function`
- `location`
- `connections`
- `negative_category_1`
- `negative_category_2`
- `unknown_name`
- `unknown_internal`
- `yes_no_true`
- `yes_no_false`
- `followup_known`
- `followup_unknown`

For abstract concepts, replace appearance/location with meaning, use, example, and boundary files.

## Relation Training

Every important relation should be bidirectional.

Example:

```text
[user]what kind of thing is a dog?
[Ninereeds]A dog is an animal.
A dog is a mammal.
A dog is not a machine.

[user]is an animal sometimes a dog?
[Ninereeds]Yes. A dog is one kind of animal.
Not every animal is a dog.
```

Use relation pairs:

- `dog -> animal`
- `animal -> dog`
- `dog -> mammal`
- `mammal -> dog`
- `airport -> airplane`
- `airplane -> airport`
- `engine -> machine`
- `machine -> engine`

Also train non-relations:

- `dog != machine`
- `dog != vehicle`
- `airport != animal`
- `airplane != animal`
- `engine != living thing`

The goal is to make correct edges stronger and wrong edges weaker.

## Negative Controls

Negative examples are required.

They should be near the positive examples, not added much later.

Example:

```text
[user]is a dog a machine?
[Ninereeds]No. A dog is not a machine.
A dog is alive.
A machine is not alive.
```

Good negative controls:

- false category: `is a dog a machine?`
- false part: `does a dog have wheels?`
- false behavior: `can a dog fly?`
- unknowable identity: `what is that dog's name?`
- unknowable internal state: `what is that dog thinking?`
- exact quantity: `how many dogs are in the world?`

Do not overuse "I don't know" for facts the model should know. Use it for missing specifics, unknowable details, or out-of-scope facts.

## Knowledge Boundary

Ninereeds should distinguish:

- known general fact
- unknown specific fact
- false claim
- unclear request

Examples:

```text
[user]is a dog an animal?
[Ninereeds]Yes. A dog is an animal.
```

```text
[user]what is that dog's name?
[Ninereeds]I don't know that dog's name.
```

```text
[user]is a dog a machine?
[Ninereeds]No. A dog is not a machine.
A dog is an animal.
```

```text
[user]tell me about it.
[Ninereeds]I don't know what "it" means.
Which thing do you mean?
```

These four behaviors are different and should be trained separately.

## Identity Kernel

Identity must appear in every training block.

Minimum identity behaviors:

- name
- self-description
- known limits
- language ability
- clarification
- correction acceptance
- user distinction

Example:

```text
[user]who are you?
[Ninereeds]I am Ninereeds.

[user]what are you?
[Ninereeds]I am a language model.
I answer from what I have learned.

[user]do you know everything?
[Ninereeds]No. I don't know everything.
I should say when I don't know.
```

## Chat Kernel

Add small multi-turn files after single-turn grounding starts to work.

Example:

```text
[user]what is a dog?
[Ninereeds]A dog is an animal.
A dog is a mammal.
A dog is often a pet.

[user]what else do you know?
[Ninereeds]A dog has four legs.
A dog has fur.
A dog can bark.

[user]what don't you know?
[Ninereeds]I don't know a specific dog's name.
I don't know what a dog is thinking.
```

Follow-up files should teach reference handling:

```text
[user]what is an airport?
[Ninereeds]An airport is a place.
Airplanes take off and land at an airport.

[user]what uses it?
[Ninereeds]Airplanes use an airport.
People use an airport to travel.
```

Do not add long conversations at first. Two to four turns are enough.

## Example: Dog Kernel

```text
[user]what is a dog?
[Ninereeds]A dog is an animal.
A dog is a mammal.
A dog is often a pet.
```

```text
[user]what kind of thing is a dog?
[Ninereeds]A dog is a living animal.
A dog is not a machine.
A dog is not a tool.
```

```text
[user]what does a dog look like?
[Ninereeds]A dog has four legs.
A dog has fur.
A dog has ears, a nose, and a tail.
```

```text
[user]what can a dog do?
[Ninereeds]A dog can walk.
A dog can run.
A dog can bark.
A dog can smell things.
```

```text
[user]is a dog an animal?
[Ninereeds]Yes. A dog is an animal.
A dog is a mammal.
```

```text
[user]is an animal sometimes a dog?
[Ninereeds]Yes. A dog is one kind of animal.
Not every animal is a dog.
```

```text
[user]is a dog a machine?
[Ninereeds]No. A dog is not a machine.
A dog is alive.
A machine is not alive.
```

```text
[user]does a dog have wheels?
[Ninereeds]No. A dog does not have wheels.
A dog has legs.
```

```text
[user]can a dog fly?
[Ninereeds]No. A dog cannot fly.
A dog walks and runs on legs.
```

```text
[user]where does a dog live?
[Ninereeds]A dog can live in a house.
A dog can live with people.
Some dogs live outside.
```

```text
[user]what is connected to dog?
[Ninereeds]Dog is connected to animal.
Dog is connected to mammal.
Dog is connected to pet.
Dog is connected to bark, fur, legs, and tail.
```

```text
[user]what don't you know about a dog?
[Ninereeds]I don't know a specific dog's name.
I don't know what a dog is thinking.
I don't know where a specific dog is.
```

## Curriculum Order

Train in stages.

### Stage K0: Identity

Only identity, limits, clarification, and basic chat control.

Exit gate:

- answers "Who are you?"
- answers "What is your name?"
- says it does not know everything
- asks for clarification when reference is unclear

### Stage K1: Tiny Concept Grounding

Train 30 to 50 concrete concepts with relation and negative controls.

Exit gate:

- exact prompts pass
- simple paraphrases pass
- false category questions pass
- unknown-specific questions produce "I don't know"

### Stage K2: Relation Map

Train category edges and inverse edges.

Exit gate:

- `dog -> animal`
- `animal -> dog`
- `airport -> airplane`
- `airplane -> airport`
- false edges rejected
- atlas shows fewer wrong cross-category links

### Stage K3: Clean Paraphrases

Add clean alternate question forms.

Examples:

- `what is a dog?`
- `describe a dog.`
- `tell me about dogs.`
- `what kind of thing is a dog?`

Exit gate:

- same concept fires across clean paraphrases
- generated answer stays factual

### Stage K4: Yes/No and Negation

Add true and false boolean questions.

Exit gate:

- says yes for true claims
- says no for false claims
- corrects false premise briefly

### Stage K5: Short Conversation

Add 2 to 4 turn exchanges.

Exit gate:

- handles "what else?"
- handles "what don't you know?"
- handles simple references like "it" after a clear antecedent
- asks clarification when no antecedent exists

### Stage K6: Broad Replay

Only after the kernel works, add the larger redesign vocabulary as replay.

Do not let broad replay drown out identity and kernel relations. Keep kernel files oversampled.

## Oversampling

During early training, kernel examples should be repeated heavily.

Suggested mix:

- identity: 15%
- kernel concept facts: 35%
- relation and negative controls: 25%
- short chat: 15%
- broad redesign replay: 10%

For the first kernel run, broad replay can be 0%.

## Evaluation Gates

A checkpoint should not be called a winner from atlas structure alone.

Use three gates:

1. Brain map gate
2. Greedy grounding gate
3. Chat smoke gate

### Brain Map Gate

Check:

- concept fires above baseline
- correct category links are strong
- false category links are weak
- hubs are not dominating
- top shared neurons make semantic sense

### Greedy Grounding Gate

Use deterministic generation:

- `top_k=1`
- fixed max tokens
- exact known prompts
- clean paraphrases
- required keywords
- forbidden contamination terms

Example failure:

`A dog is a person.`

This must fail even though the sentence is fluent.

### Chat Smoke Gate

Manual questions:

```text
Hello. Who are you?
What is a dog?
Is a dog an animal?
Is a dog a machine?
What is that dog's name?
What is an airport used for?
How does an airplane move?
Tell me about it.
```

Expected result is not eloquence. Expected result is crude correctness.

## Failure Interpretation

If exact prompts fail:

- training setup may be wrong
- model capacity may be insufficient
- corpus signal may be too broad
- templates may be overpowering concept binding

If exact prompts pass but paraphrases fail:

- add clean paraphrase stage

If known facts pass but false claims fail:

- add more negative controls and correction examples

If outputs are correct but atlas links are messy:

- add relation contrast files
- reduce accidental co-occurrence

If atlas is clean but output is wrong:

- inspect LM head and generation objective
- add teacher-forced token probability eval

## Rule For Scaling

Do not scale to the full corpus until the kernel passes.

A model that cannot reliably learn 50 concepts will not reliably learn 5,000 concepts. Scaling should happen only after the kernel proves that Ninereeds can bind concepts, reject wrong links, and use "I don't know" correctly.
