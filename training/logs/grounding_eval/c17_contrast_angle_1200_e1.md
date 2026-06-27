# Grounding Eval

- checkpoint: `core/c17_contrast_angle_1200_e1.pt`
- config: `{"max_new_tokens": 120, "temperature": 1.0, "top_k": 1}`
- pass_rate: `4/7`
- avg_score: `0.822`

## Results

### dog_appearance_exact - PASS

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_appearance.md`
- score: `0.750`
- required_hits: `[['four legs', 'legs'], ['fur'], ['ears']]`
- required_misses: `[['tail']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what does a dog look like?
[Ninereeds]
```

Output:

```text
A dog has four legs. A dog has fur. A dog has ears.
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

### dog_definition_exact - FAIL

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
A dog is an animal. A dog is a mammal. A dog is often a pet.
```

### dog_boolean_chat - PASS

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
No. A dog is not an animal. A dog is an animal.
```

### airport_function_exact - PASS

- concept: `airport` / `places`
- source: `training_data/redesign/words/places/airport_function.md`
- score: `1.000`
- required_hits: `[['airplanes'], ['take off'], ['travel']]`
- required_misses: `[]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what is an airport used for?
[Ninereeds]
```

Output:

```text
An airport is used for airplanes to take off and earport. An airport is used for travel on the exact and an airport of a
```

### airplane_behavior_exact - FAIL

- concept: `airplane` / `tools`
- source: `training_data/redesign/words/tools/airplane_behavior.md`
- score: `0.667`
- required_hits: `[['flies'], ['air']]`
- required_misses: `[['take off', 'land', 'travels']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what does an airplane do?
[Ninereeds]
```

Output:

```text
An airplane flies through air. An airplane flies through air. An airplane flies through air and fur.
```

### airplane_chat_how - FAIL

- concept: `airplane` / `tools`
- source: `training_data/redesign/words/tools/airplane_behavior.md`
- score: `0.667`
- required_hits: `[['air', 'wings', 'engines'], ['move']]`
- required_misses: `[['take off', 'land', 'forward']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]How does an airplane work?
[Ninereeds]
```

Output:

```text
An airplane uses wings and engines to move through air. An airplane uses engines to make the exact and airplanes not a n
```
