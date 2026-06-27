# Grounding Eval

- checkpoint: `core/kernel_e0_scratch.pt`
- config: `{"max_new_tokens": 120, "temperature": 1.0, "top_k": 1}`
- pass_rate: `0/7`
- avg_score: `0.107`

## Results

### ground_dog_appearance_exact - FAIL

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_appearance.md`
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['four legs', 'legs'], ['fur', 'hair'], ['tail'], ['snout', 'ears', 'nose']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what does a dog look like?
[Ninereeds]
```

Output:

```text
A doctor have on a specific name. A doctor helps sick people. A doctor knows medicines to speak.
```

### ground_dog_classification_exact - FAIL

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_classification.md`
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['animal'], ['mammal', 'pet']]`
- forbidden_hits: `['person']`

Prompt:

```text
[user]what kind of thing is a dog?
[Ninereeds]
```

Output:

```text
A doctor is a person. A doctor is not a person. A doctor helps sick people. A doctor have the acts.
```

### ground_dog_definition_exact - FAIL

- concept: `dog` / `animals`
- source: `training_data/redesign/words/animals/dog_what_is.md`
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['animal'], ['four legs', 'legs'], ['fur', 'barks', 'pet', 'people']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what is a dog?
[Ninereeds]
```

Output:

```text
A dog has wheels. A dog has wings. A dog has wings.
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
No. A dog is an animal. A dog is a place. A dog is an animal.
```

### ground_airport_function_exact - FAIL

- concept: `airport` / `places`
- source: `training_data/redesign/words/places/airport_function.md`
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['airplane', 'airplanes', 'plane', 'planes'], ['take off', 'land', 'landing'], ['travel', 'cargo']]`
- forbidden_hits: `['person']`

Prompt:

```text
[user]what is an airport used for?
[Ninereeds]
```

Output:

```text
I do not know. I do not know the specific person come from. I only know the specific water comething.
```

### ground_airplane_behavior_exact - FAIL

- concept: `airplane` / `tools`
- source: `training_data/redesign/words/tools/airplane_behavior.md`
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['moves', 'move', 'flies', 'fly'], ['air'], ['take off', 'land', 'travels']]`
- forbidden_hits: `['tree']`

Prompt:

```text
[user]what does an airplane do?
[Ninereeds]
```

Output:

```text
An airport has runways. An airport is a place where people can live in a house. I do not know the specific tree in a sto
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
An airport has runways. An airport is a place where people learn. An airport has parts. An airport has runwa school.

[u
```
