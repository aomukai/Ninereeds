# Grounding Eval

- checkpoint: `core/c17_ladder_1200_e1.pt`
- config: `{"max_new_tokens": 120, "temperature": 1.0, "top_k": 1}`
- pass_rate: `3/7`
- avg_score: `0.595`

## Results

### dog_appearance_exact - FAIL

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_appearance.md`
- score: `0.500`
- required_hits: `[['four legs', 'legs'], ['fur']]`
- required_misses: `[['tail'], ['snout', 'ears', 'nose']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what does a dog look like?
[Ninereeds]
```

Output:

```text
A dog has flat lives. A dog has four legs. A dog has fur.
```

### dog_classification_exact - PASS

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_classification.md`
- score: `1.000`
- required_hits: `[['animal'], ['mammal', 'pet']]`
- required_misses: `[]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what kind of thing is a dog?
[Ninereeds]
```

Output:

```text
A dog is an animal. A dog is a mammal. A dog is often a pet.
```

### dog_definition_exact - PASS

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_what_is.md`
- score: `1.000`
- required_hits: `[['animal'], ['four legs', 'legs'], ['pet']]`
- required_misses: `[]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what is a dog?
[Ninereeds]
```

Output:

```text
A dog is an animal. A dog is a mammal. A dog is often a pet. A dog has four legs and a tool.
```

### dog_boolean_chat - PASS

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_classification.md`
- score: `1.000`
- required_hits: `[['yes', 'animal']]`
- required_misses: `[]`
- forbidden_hits: `[]`

Prompt:

```text
[user]Is a dog an animal?
[Ninereeds]
```

Output:

```text
Yes. A dog is an animal. A dog is a mammal.
```

### airport_function_exact - FAIL

- concept: `airport` / `places`
- source: `training_data/redesign/words/places/airport_function.md`
- score: `0.333`
- required_hits: `[['airplanes']]`
- required_misses: `[['take off', 'land', 'landing'], ['travel', 'cargo']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what is an airport used for?
[Ninereeds]
```

Output:

```text
An airport is used for airplanes to make from airplanes are used for an airport. A tairplane is used for an airports are
```

### airplane_behavior_exact - FAIL

- concept: `airplane` / `tools`
- source: `training_data/redesign/words/tools/airplane_behavior.md`
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['moves', 'move', 'flies', 'fly'], ['air'], ['take off', 'land', 'travels']]`
- forbidden_hits: `['animal']`

Prompt:

```text
[user]what does an airplane do?
[Ninereeds]
```

Output:

```text
An airplane flys are found on an animals. An airplane flows and a part of an animal. An airport is a part of an airport.
```

### airplane_chat_how - FAIL

- concept: `airplane` / `tools`
- source: `training_data/redesign/words/tools/airplane_behavior.md`
- score: `0.333`
- required_hits: `[['wings']]`
- required_misses: `[['fly', 'flies', 'move', 'moves', 'lift'], ['take off', 'land', 'forward']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]How does an airplane work?
[Ninereeds]
```

Output:

```text
An airplane uses wings and a tail. An airplane has a tail. An airplane has a tail.
```
