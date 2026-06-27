# Grounding Eval

- checkpoint: `core/kernel_e1_jsonl_continue.pt`
- config: `{"max_new_tokens": 120, "temperature": 1.0, "top_k": 1}`
- pass_rate: `1/7`
- avg_score: `0.536`

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
A dog barkswled places. A dog lives energy. A body is the place.
```

### ground_dog_classification_exact - PASS

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
A dog is an animal. A dog is a mammal. A dog is a pet.
```

### ground_dog_definition_exact - FAIL

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_what_is.md`
- score: `0.667`
- required_hits: `[['animal'], ['fur']]`
- required_misses: `[['four legs', 'legs']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what is a dog?
[Ninereeds]
```

Output:

```text
A dog is an animal. A dog is a mammal. A dog has fur.
```

### ground_dog_boolean_chat - FAIL

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_classification.md`
- score: `0.750`
- required_hits: `[['animal']]`
- required_misses: `[]`
- forbidden_hits: `['place']`

Prompt:

```text
[user]Is a dog an animal?
[Ninereeds]
```

Output:

```text
No. A dog is an animal. A dog is not a place.
```

### ground_airport_function_exact - FAIL

- concept: `airport` / `places`
- source: `training_data/redesign/words/places/airport_function.md`
- score: `0.667`
- required_hits: `[['airplanes'], ['take off', 'land']]`
- required_misses: `[['travel', 'cargo']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what is an airport used for?
[Ninereeds]
```

Output:

```text
An airport is a place. Airplanes take off and land at an airport. An airport has runways.
```

### ground_airplane_behavior_exact - FAIL

- concept: `airplane` / `tools`
- source: `training_data/redesign/words/tools/airplane_behavior.md`
- score: `0.667`
- required_hits: `[['moves', 'flies'], ['air']]`
- required_misses: `[['take off', 'land', 'travels']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what does an airplane do?
[Ninereeds]
```

Output:

```text
An airplane flies through air. It can carry people or cargo. It moves forward using its chools. It can be the sickes not
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
An airplane does not have a machine art in a specific arplanguat. It has related to ovethings a parkshoates.
```
