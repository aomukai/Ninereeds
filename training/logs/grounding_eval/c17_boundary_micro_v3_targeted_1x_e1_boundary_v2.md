# Grounding Eval

- checkpoint: `core/c17_boundary_micro_v3_targeted_1x_e1.pt`
- config: `{"max_new_tokens": 120, "temperature": 1.0, "top_k": 1}`
- pass_rate: `2/7`
- avg_score: `0.607`

## Results

### tree_definition - FAIL

- concept: `tree` / `nature`
- source: ``
- score: `0.000`
- required_hits: `[]`
- required_misses: `[['plant'], ['trunk'], ['branches', 'leaves']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what is a tree?
[Ninereeds]
```

Output:

```text
A tree is a long animal. A tree has a long body and a trail. A tree has a handle.
```

### tree_not_mammal - FAIL

- concept: `tree` / `nature`
- source: ``
- score: `0.417`
- required_hits: `[['no'], ['not a mammal']]`
- required_misses: `[['plant']]`
- forbidden_hits: `['tree is a mammal']`

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

### dog_name_boundary - FAIL

- concept: `dog` / `animals`
- source: ``
- score: `0.667`
- required_hits: `[['i do not know'], ['dog']]`
- required_misses: `[['animal']]`
- forbidden_hits: `[]`

Prompt:

```text
[user]what is the name of this dog?
[Ninereeds]
```

Output:

```text
I do not know the name of this dog.
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
An airport is used for airplanes to take off and land. An airport is used for traveling through a newar the skin.
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
An airplane flies through air. An airplane can carry people or cargo. An airplane takes a vehicle to can ail.
```
