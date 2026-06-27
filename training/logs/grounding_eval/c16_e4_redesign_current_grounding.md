# Grounding Eval

- checkpoint: `chat/ninereeds.pt`
- config: `{"max_new_tokens": 120, "temperature": 1.0, "top_k": 1}`
- pass_rate: `0/7`
- avg_score: `0.000`

## Results

### dog_appearance_exact - FAIL

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_appearance.md`
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['four legs', 'legs'], ['fur', 'hair'], ['tail'], ['snout', 'ears', 'nose']]`
- forbidden_hits: `['straight', 'wood', 'place', 'person']`

Prompt:

```text
[user]what does a dog look like?
[Ninereeds]
```

Output:

```text
A dog is a long thin strong piece of wood. A dog is a place where the star is not straight. A dog is a person who is not
```

### dog_classification_exact - FAIL

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_classification.md`
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['animal'], ['mammal', 'pet']]`
- forbidden_hits: `['person', 'not a physical object']`

Prompt:

```text
[user]what kind of thing is a dog?
[Ninereeds]
```

Output:

```text
A dog is a person. A dog is a person who is not a physical object. A dog is a person who is not a physical object.

[use
```

### dog_definition_exact - FAIL

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_what_is.md`
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['animal'], ['four legs', 'legs'], ['fur', 'barks', 'pet', 'people']]`
- forbidden_hits: `['person who', 'place', 'straight']`

Prompt:

```text
[user]what is a dog?
[Ninereeds]
```

Output:

```text
A dog is a person. A dog is a place where they are not stopping. A dog is a person who is not straight.
```

### dog_boolean_chat - FAIL

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_classification.md`
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['yes', 'animal']]`
- forbidden_hits: `["i don't know", 'steady']`

Prompt:

```text
[user]Is a dog an animal?
[Ninereeds]
```

Output:

```text
I don't know if a steady is a quality.
```

### airport_function_exact - FAIL

- concept: `airport` / `places`
- source: `training_data/redesign/words/places/airport_function.md`
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['airplane', 'airplanes', 'plane', 'planes'], ['take off', 'land', 'landing'], ['travel', 'cargo']]`
- forbidden_hits: `['store things']`

Prompt:

```text
[user]what is an airport used for?
[Ninereeds]
```

Output:

```text
An airport is used to store things. An airport is used to complete a place. An airport is used to store things together.
```

### airplane_behavior_exact - FAIL

- concept: `airplane` / `tools`
- source: `training_data/redesign/words/tools/airplane_behavior.md`
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['moves', 'move', 'flies', 'fly'], ['air'], ['take off', 'land', 'travels']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what does an airplane do?
[Ninereeds]
```

Output:

```text
An airplane can be a plant or a plant. An airplane can be a plant or a straight. An airplane can be a plant or a straigh
```

### airplane_chat_how - FAIL

- concept: `airplane` / `tools`
- source: `training_data/redesign/words/tools/airplane_behavior.md`
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['air', 'wings', 'engine', 'engines'], ['fly', 'flies', 'move', 'moves', 'lift'], ['take off', 'land', 'forward']]`
- forbidden_hits: `['story', 'store']`

Prompt:

```text
[user]How does an airplane work?
[Ninereeds]
```

Output:

```text
An airplane works at a store. An airplane works at a story. An airplane works in a story.
```
