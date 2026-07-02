# MSM Tutor Loop

The tutor loop is the per-card teaching pattern used by the active MSM pipeline.

It is not free chat. It is a scripted or explicitly adaptive teaching session that
produces raw logs, turn grades, a report card, and optionally proposed training turns.

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

- Orchestrator chooses the card, session type, and target axes.
- DeepSeek writes the script and later fills the report card.
- Gemma executes fixed scripts only.
- DeepSeek may run an adaptive session only when the orchestrator explicitly requests it.

Gemma never decides the next prompt.

---

## Concept Card

```json
{
  "card_id": "cat",
  "concept": "cat",
  "category": "animals",
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

## Correction Style

Correction turns are short and staged:

```text
[user] A cat is an animal. A dog is an animal. A cat is not a dog.
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

Every scripted item should provide enough metadata for DeepSeek to grade consistently:

```json
{
  "turn_id": "t004",
  "stage": "or_question",
  "prompt": "[user]Is a cat a dog?\n[Ninereeds]",
  "expected_answer": "A cat is not a dog. A cat is a cat.",
  "required": [["cat"], ["not a dog"]],
  "forbidden": ["cat is a dog"],
  "target_failure_modes": ["same_category_confusion"],
  "training_answer_max_bytes": 96
}
```

Only short proposed `training_answer` fields can enter `proposed_training.jsonl`.
The orchestrator must approve them before they enter an update buffer. Diagnostic
explanations are logs only.

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

DeepSeek-proposed correction or expected-answer turns may enter `proposed_training.jsonl`
after grading. They may enter `approved_training.jsonl` only after orchestrator acceptance.
