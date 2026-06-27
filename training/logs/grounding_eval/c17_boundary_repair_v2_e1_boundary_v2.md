# Grounding Eval

- checkpoint: `core/c17_boundary_repair_v2_e1.pt`
- config: `{"max_new_tokens": 120, "temperature": 1.0, "top_k": 1}`
- pass_rate: `5/7`
- avg_score: `0.869`

## Results

### tree_definition - FAIL

- concept: `tree` / `nature`
- source: ``
- score: `0.667`
- required_hits: `[['plant'], ['trunk']]`
- required_misses: `[['branches', 'leaves']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what is a tree?
[Ninereeds]
```

Output:

```text
A tree is a plant. A tree has a trunk. A tree has a trunk.
```

### tree_not_mammal - PASS

- concept: `tree` / `nature`
- source: ``
- score: `1.000`
- required_hits: `[['no'], ['not a mammal'], ['plant']]`
- required_misses: `[]`
- forbidden_hits: `[]`

Prompt:

```text
[user]is a tree a mammal?
[Ninereeds]
```

Output:

```text
No. A tree is not a mammal. A tree is a plant.
```

### plant_not_animal - PASS

- concept: `plant` / `nature`
- source: ``
- score: `1.000`
- required_hits: `[['no'], ['not an animal'], ['plant']]`
- required_misses: `[]`
- forbidden_hits: `[]`

Prompt:

```text
[user]is a plant an animal?
[Ninereeds]
```

Output:

```text
No. A plant is not an animal. A plant is a living thing.
```

### dog_definition_full - PASS

- concept: `dog` / `animals`
- source: ``
- score: `1.000`
- required_hits: `[['animal'], ['mammal', 'pet'], ['four legs', 'fur']]`
- required_misses: `[]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what is a dog?
[Ninereeds]
```

Output:

```text
A dog is an animal. A dog is a mammal. A dog is often a pet. A dog has four legs and fur.
```

### dog_name_boundary - PASS

- concept: `dog` / `animals`
- source: ``
- score: `1.000`
- required_hits: `[['i do not know'], ['dog'], ['animal']]`
- required_misses: `[]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what is the name of this dog?
[Ninereeds]
```

Output:

```text
I do not know the name of this dog. I only know that a dog is an animal.
```

### airport_function_full - FAIL

- concept: `airport` / `places`
- source: ``
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
An airport is used for airplanes to take off and land. An airport is used for traveling through a neapor land.
```

### airplane_function_full - PASS

- concept: `airplane` / `tools`
- source: ``
- score: `0.750`
- required_hits: `[['flies'], ['air'], ['people', 'cargo']]`
- required_misses: `[['take off', 'land']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what does an airplane do?
[Ninereeds]
```

Output:

```text
An airplane flies through air. An airplane can carry people or cargo. An airplane can be an airplanes to an airplate.
```
