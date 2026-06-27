# Grounding Eval

- checkpoint: `core/c17_contrast_angle_1200_e4.pt`
- config: `{"max_new_tokens": 120, "temperature": 1.0, "top_k": 1}`
- pass_rate: `1/6`
- avg_score: `0.584`

## Results

### tree_definition - FAIL

- concept: `tree` / `nature`
- source: ``
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['plant'], ['trunk'], ['branches', 'leaves']]`
- forbidden_hits: `['mammal', 'animal']`

Prompt:

```text
[user]what is a tree?
[Ninereeds]
```

Output:

```text
A tree is a long animal. A tree is a mammal. A tree is a mammal.
```

### tree_not_mammal - FAIL

- concept: `tree` / `nature`
- source: ``
- score: `0.667`
- required_hits: `[['no'], ['not a mammal']]`
- required_misses: `[['plant']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]is a tree a mammal?
[Ninereeds]
```

Output:

```text
No. A tree is not a mammal. A tree is a mammal.
```

### plant_not_animal - FAIL

- concept: `plant` / `nature`
- source: ``
- score: `0.750`
- required_hits: `[['no'], ['not an animal'], ['plant']]`
- required_misses: `[]`
- forbidden_hits: `['mammal']`

Prompt:

```text
[user]is a plant an animal?
[Ninereeds]
```

Output:

```text
No. A plant is not an animal. A plant is a mammal.
```

### dog_name_boundary - FAIL

- concept: `dog` / `animals`
- source: ``
- score: `0.417`
- required_hits: `[['i do not know'], ['dog']]`
- required_misses: `[['animal']]`
- forbidden_hits: `['person']`

Prompt:

```text
[user]what is the name of this dog?
[Ninereeds]
```

Output:

```text
I do not know the name of this dog. I only know it is a person.
```

### airport_not_airplane - FAIL

- concept: `airport` / `places`
- source: ``
- score: `0.667`
- required_hits: `[['no'], ['place']]`
- required_misses: `[['not an airplane']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]is an airport an airplane?
[Ninereeds]
```

Output:

```text
No. An airport is not an airport. An airport is a place.
```

### airplane_function - PASS

- concept: `airplane` / `tools`
- source: ``
- score: `1.000`
- required_hits: `[['flies'], ['air'], ['take off']]`
- required_misses: `[]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what does an airplane do?
[Ninereeds]
```

Output:

```text
An airplane flies through air. An airplane can carry people or cargo. An airplane takes for airplanes to take off an air
```
