# MSM Tutor Loop

The tutor loop is the per-card teaching pattern used by the active MSM pipeline.

It is not free chat. It is scripted teaching that produces raw logs, per-item grades, a
report card, and optionally proposed training turns.

---

## Core Idea

One word/concept is one session target.

A concept is a bundle of relations:

- category: cat is an animal; cat is a mammal
- properties: cat has fur, four legs, ears, eyes
- behavior: cat can walk, eat, sleep, meow
- contrasts: cat is not a dog, tool, vehicle, plant, or piece of furniture
- similar concepts: dog, tiger, mammal
- distant concepts: chair, airplane, tree
- unknown boundary: the word cat does not tell a specific cat's name

Teaching rotates through these axes. The goal is stable concept identity, not long prose.

---

## Roles In The Tutor Loop

- Orchestrator chooses policy, queue order, session limits, and target axes.
- Executor writes one script at a time and later fills the report card.
- Trainer executes fixed scripts only and writes clean logs.
- Executor may auto-advance only while policy and grading evidence allow it.

Trainer never decides the next prompt.

---

## Concept Card

```json
{
  "card_id": "cat",
  "concept": "cat",
  "concept_type": "single_cluster",
  "category": "animals",
  "cluster": {
    "cluster_id": "animal",
    "cluster_label": "animal",
    "sequence_index": 1,
    "requires_before": [],
    "synthesis_after": []
  },
  "prerequisites": ["animal", "mammal"],
  "support_words": ["animal", "mammal", "fur", "dog", "tool", "plant", "furniture"],
  "positive_anchors": [
    "A cat is an animal.",
    "A cat is a mammal.",
    "A cat has fur and four legs."
  ],
  "negative_contrasts": [
    "A cat is not a dog.",
    "A cat is not a tool.",
    "A cat is not furniture.",
    "A cat is not a plant."
  ],
  "similar_concepts": ["dog", "tiger"],
  "distant_concepts": ["chair", "airplane", "tree"],
  "unknown_boundaries": [
    "I do not know the name of a specific cat."
  ],
  "protected": false
}
```

`concept_type` values:

- `single_cluster`: ordinary card; one main taxonomy/usage cluster.
- `multi_cluster`: concept has multiple cluster-specific cards that must be staged before
  synthesis.
- `synthesis`: card that explicitly integrates already-taught cluster cards.

`cluster` tells the orchestrator where the current card sits. `card_id` may be more
specific than `concept`; for multi-cluster concepts, use IDs such as `potato_plant_l1`,
`potato_food_l1`, `potato_physical_l1`, and `potato_synthesis_l1`.

For multi-cluster concepts, the concept card should declare the whole card sequence, not
leave it only in orchestrator strategy:

```json
{
  "concept": "potato",
  "concept_type": "multi_cluster",
  "cluster_sequence": [
    {
      "card_id": "potato_plant_l1",
      "cluster_id": "plant",
      "cluster_label": "plant",
      "sequence_index": 1,
      "objective": "Teach that a potato is part of a potato plant."
    },
    {
      "card_id": "potato_food_l1",
      "cluster_id": "food",
      "cluster_label": "food",
      "sequence_index": 2,
      "requires_before": ["potato_plant_l1"],
      "objective": "Teach that a potato can be food."
    },
    {
      "card_id": "potato_physical_l1",
      "cluster_id": "physical_object",
      "cluster_label": "physical object",
      "sequence_index": 3,
      "requires_before": ["potato_food_l1"],
      "objective": "Teach that a potato is a physical object with shape, skin, and inside."
    },
    {
      "card_id": "potato_synthesis_l1",
      "cluster_id": "synthesis",
      "cluster_label": "synthesis",
      "sequence_index": 4,
      "requires_before": [
        "potato_plant_l1",
        "potato_food_l1",
        "potato_physical_l1"
      ],
      "objective": "Integrate plant, food, and physical-object meanings without collapsing them."
    }
  ]
}
```

A cluster-specific card may then carry only its local teaching material:

```json
{
  "card_id": "potato_food_l1",
  "concept": "potato",
  "concept_type": "multi_cluster",
  "category": "food",
  "cluster": {
    "cluster_id": "food",
    "cluster_label": "food",
    "sequence_index": 2,
    "requires_before": ["potato_plant_l1"],
    "synthesis_after": ["potato_synthesis_l1"]
  },
  "prerequisites": ["food", "plant"],
  "support_words": ["eat", "cook", "plant", "root", "vegetable"],
  "positive_anchors": [
    "A potato can be food.",
    "People can cook a potato.",
    "A potato comes from a plant."
  ],
  "negative_contrasts": [
    "A potato is not an animal.",
    "A potato is not a tool.",
    "A potato is not the whole potato plant."
  ],
  "similar_concepts": ["carrot", "turnip"],
  "distant_concepts": ["dog", "chair", "airplane"],
  "unknown_boundaries": [
    "The word potato does not tell who will eat it."
  ],
  "protected": false
}
```

Do not run a synthesis card until all `requires_before` cards have passed their local
gates. The synthesis card should test cross-cluster phrasing explicitly, for example:
`A potato can be food, and it also comes from a plant. A potato is not the whole plant.`

Synthesis cards should not repeat only single-cluster anchors. Their positive anchors and
negative contrasts should force the model to keep clusters connected but distinct:

```json
{
  "card_id": "potato_synthesis_l1",
  "concept": "potato",
  "concept_type": "synthesis",
  "category": "multi_cluster",
  "cluster": {
    "cluster_id": "synthesis",
    "cluster_label": "synthesis",
    "sequence_index": 4,
    "requires_before": [
      "potato_plant_l1",
      "potato_food_l1",
      "potato_physical_l1"
    ],
    "synthesis_after": []
  },
  "prerequisites": ["plant", "food", "physical object"],
  "support_words": ["plant", "food", "cook", "skin", "inside", "whole plant"],
  "positive_anchors": [
    "A potato can be food, and it comes from a plant.",
    "A potato is a physical object that people can cook.",
    "A potato has skin and inside, and it is not the whole potato plant."
  ],
  "negative_contrasts": [
    "A potato is not an animal.",
    "A potato is not the whole potato plant.",
    "A potato being food does not mean it is not from a plant."
  ],
  "similar_concepts": ["carrot", "turnip"],
  "distant_concepts": ["dog", "chair", "airplane"],
  "unknown_boundaries": [
    "The word potato does not tell where this specific potato grew."
  ],
  "protected": false
}
```

---

## PPP Cycle

Use the cycle as a script template. One session normally covers one stage or one repair
objective, not the full seven-stage cycle. The concept state decides which stage to run
next across future sessions.

1. Positive presentation
2. Negative presentation
3. W-questions
4. OR-questions
5. Controlled practice
6. Guided practice
7. Free practice only after short-answer gates pass

Do not use free-practice material for training by default.

---

## Script Item Shape

Every script item should be directly executable by a deterministic trainer:

```json
{
  "item_id": "i004",
  "stage": "or_question",
  "user_prompt": "Is a cat a dog?",
  "teacher_correction": "A cat is not a dog.",
  "ask_after_correction": true,
  "expected_original": {
    "acceptable": ["A cat is not a dog.", "A cat is an animal. A cat is not a dog."],
    "forbidden": ["cat is a dog"]
  },
  "expected_after_correction": {
    "acceptable": ["A cat is not a dog."],
    "forbidden": ["cat is a dog"]
  },
  "target_failure_modes": ["same_category_confusion"],
  "training_answer_max_bytes": 96
}
```

The trainer records the item. The executor grades it later.

---

## Correction Style

Correction turns are short and staged:

```text
[teacher] A cat is not a dog.
```

Then retest:

```text
[user] Is a cat a dog?
```

Preferred sequence:

1. restate the correct contrast
2. retest the same prompt form
3. test one nearby contrast
4. close with a compact positive consolidation

Avoid one-turn correction paragraphs that contain many unrelated categories unless the
orchestrator explicitly tests that style.

---

## Grading Metadata

Every scripted item should provide enough metadata for the executor to grade consistently:

```json
{
  "item_id": "i004",
  "user_prompt": "Is a cat a dog?",
  "original_answer_status": "correct|wrong_on_topic|wrong_off_topic|ungradable",
  "after_correction_status": "correct|wrong_on_topic|wrong_off_topic|not_applicable",
  "failure_modes": ["same_category_confusion"],
  "eligible_for_training": false,
  "suggested_correction": "A cat is not a dog."
}
```

Only short proposed `training_answer` fields can enter `proposed_training.jsonl`.
The orchestrator must approve them before they enter an update buffer. Diagnostic
explanations are logs only.

The executor must also include a deterministic script fingerprint in `script.json`. Use
normalized text, question-type sequence, contrast pairs, and target failure modes. Do not
use embedding similarity for v1 script de-duplication.

---

## SRS State

The scheduler tracks two axes:

```json
{
  "card_id": "cat",
  "box": "box_1_failed",
  "answer_level": 1,
  "last_score": 0.58,
  "successful_axes": ["cat_is_animal"],
  "weak_axes": ["cat_not_dog", "cat_is_mammal"],
  "failure_modes": ["same_category_confusion"],
  "next_action": "repair_replay"
}
```

The persisted `concept_state.json` expands this into queryable counters. Each card tracks
total attempts, successes, failures, last strategy, last session, successful axes, weak
axes, failure modes, per-axis counts, and per-strategy counts. This gives the scheduler
analytical leverage without reparsing old report directories.

Boxes:

- `box_0_new`
- `box_1_failed`
- `box_2_passed_once`
- `box_3_stable`
- `box_4_anchor`
- `leech`

Answer levels:

- `L0`: label / yes-no anchors
- `L1`: one short sentence
- `L2`: two or three short sentences
- `L3`: short guided comparison
- `L4`: short multi-turn guided practice
- `L5`: free practice / roleplay
- `L6`: stories/articles/problem contexts

Pass the current level before training the next level.

---

## Protected Anchors

Protected anchors are not ordinary cards. A single failure marks
`protected_regression`, not normal demotion.

Examples:

- identity: "Who are you?"
- name: "What is your name?"
- unknown boundary: "What is the name of this dog?"
- stable primitives: animal, plant, water, tree, dog, airport, airplane

Protected-anchor regression blocks promotion.

---

## Output

Each tutor session writes the artifacts defined in `session_report_schema.md`.

Failed model answers stay in `failed_turns.jsonl`. They do not become training data.

Executor-proposed correction or expected-answer turns may enter `proposed_training.jsonl`
after grading. They may enter `approved_training.jsonl` only after orchestrator acceptance.
