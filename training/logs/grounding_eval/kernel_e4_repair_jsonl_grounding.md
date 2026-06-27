# Grounding Eval

- checkpoint: `core/kernel_e4_repair_jsonl.pt`
- config: `{"max_new_tokens": 120, "temperature": 1.0, "top_k": 1}`
- pass_rate: `3/7`
- avg_score: `0.524`

## Results

### ground_dog_appearance_exact - FAIL

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_appearance.md`
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['four legs', 'legs'], ['fur', 'hair'], ['tail'], ['snout', 'ears', 'nose']]`
- forbidden_hits: `['place']`

Prompt:

```text
[user]what does a dog look like?
[Ninereeds]
```

Output:

```text
A dog is a long thin and the hand. A dog is a place with a feet.
```

### ground_dog_classification_exact - PASS

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_classification.md`
- score: `1.000`
- required_hits: `[['animal'], ['pet']]`
- required_misses: `[]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what kind of thing is a dog?
[Ninereeds]
```

Output:

```text
A dog is an animal. A dog is a pet.
```

### ground_dog_definition_exact - FAIL

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_what_is.md`
- score: `0.667`
- required_hits: `[['animal'], ['pet']]`
- required_misses: `[['four legs', 'legs']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what is a dog?
[Ninereeds]
```

Output:

```text
A dog is an animal. A dog is a mammal. A dog is a pet.
```

### ground_dog_boolean_chat - PASS

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_classification.md`
- score: `1.000`
- required_hits: `[['animal']]`
- required_misses: `[]`
- forbidden_hits: `[]`

Prompt:

```text
[user]Is a dog an animal?
[Ninereeds]
```

Output:

```text
No. A dog is an animal. A dog is not an animal.
```

### ground_airport_function_exact - FAIL

- concept: `airport` / `places`
- source: `training_data/redesign/words/places/airport_function.md`
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['airplane', 'airplanes', 'plane', 'planes'], ['take off', 'land', 'landing'], ['travel', 'cargo']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what is an airport used for?
[Ninereeds]
```

Output:

```text
An airport is used to see. An airport is used to speak or walk. An airport is used to share things. An airport is used t
```

### ground_airplane_behavior_exact - PASS

- concept: `airplane` / `tools`
- source: `training_data/redesign/words/tools/airplane_behavior.md`
- score: `1.000`
- required_hits: `[['flies'], ['air'], ['land']]`
- required_misses: `[]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what does an airplane do?
[Ninereeds]
```

Output:

```text
An airplane flies through air. It can carry people or plants. It can burn off and land are in its hand.
```

### ground_airplane_chat_how - FAIL

- concept: `airplane` / `tools`
- source: `training_data/redesign/words/tools/airplane_behavior.md`
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['air', 'wings', 'engine', 'engines'], ['fly', 'flies', 'move', 'moves', 'lift'], ['take off', 'land', 'forward']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]How does an airplane work?
[Ninereeds]
```

Output:

```text
An airplane works in a face. It does not grow and does not need food. It does not give an exact number.
```
