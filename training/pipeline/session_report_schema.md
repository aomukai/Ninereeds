# MSM Session Report Schema

DeepSeek fills these artifacts after every session. The orchestrator reads the JSON.

Machine-readable schema: `training/pipeline/session_report_schema.json`.
Training-turn record schema: `training/pipeline/training_turn_schema.json`.

---

## `report_card.json`

Required top-level fields:

```json
{
  "schema_version": "msm_session_report_v1",
  "session_id": "string",
  "concept": "string",
  "card_id": "string",
  "checkpoint_before": "string",
  "checkpoint_after": "string|null",
  "session_mode": "scripted_gemma_session|deepseek_adaptive_session|probe_session|repair_replay_session|contrast_session|protected_anchor_session",
  "script": {
    "script_id": "string",
    "script_author": "string",
    "script_mode": "fixed|adaptive_plan",
    "orchestrator_plan_id": "string",
    "intended_stage": "string",
    "intended_failure_targets": ["string"]
  },
  "counts": {
    "total_turns": 0,
    "ninereeds_answer_turns": 0,
    "correct": 0,
    "partially_correct": 0,
    "incorrect": 0,
    "on_topic": 0,
    "off_topic": 0,
    "malformed": 0,
    "repetition_collapse": 0,
    "empty_or_near_empty": 0
  },
  "scores": {
    "correct_rate": 0.0,
    "on_topic_rate": 0.0,
    "malformed_rate": 0.0,
    "session_passed": false
  },
  "failure_modes": [],
  "successful_axes": [],
  "weak_axes": [],
  "protected_anchor_status": {
    "tested": false,
    "passed": null,
    "failures": []
  },
  "recommended_extraction": {
    "proposed_training_turns": 0,
    "rejected_turns": 0,
    "extraction_file": "proposed_training.jsonl|null",
    "do_not_train_raw_log": true
  },
  "deepseek_recommendation": {
    "recommendation_type": "accept|continue|repair_replay|probe|brain_scan|micro_update|escalate|reject",
    "suggested_next_session_mode": "string|null",
    "suggested_focus": [],
    "requires_orchestrator_decision": true,
    "requires_human_attention": false
  },
  "artifacts": {
    "raw_log": "raw_chat.jsonl",
    "script": "script.json",
    "report_md": "report.md",
    "turn_grades": "turn_grades.jsonl",
    "proposed_training": "proposed_training.jsonl|null",
    "failed_turns": "failed_turns.jsonl"
  }
}
```

For `scripted_gemma_session`, `script_mode` is `fixed` and `script_deviation` applies.
For `deepseek_adaptive_session`, `script_mode` is `adaptive_plan`; `script.json` records
the intended plan and `script_deviation` should not be used for normal adaptive turns.

`card_id` and `concept` may be identical for simple cards. They may diverge when one
concept has multiple teaching cards, such as `cat_boundary_l1` for concept `cat`.

---

## Failure Mode Object

```json
{
  "type": "same_category_confusion",
  "severity": "low|medium|high|critical",
  "turn_ids": ["t006"],
  "example": "A cat is a dog.",
  "interpretation": "Cat and dog share animal category, but identity boundary failed."
}
```

Common failure types:

- `missing_anchor`
- `wrong_attractor`
- `same_category_confusion`
- `cross_category_confusion`
- `unknown_boundary_failure`
- `identity_failure`
- `topic_drift`
- `malformed_language`
- `repetition_collapse`
- `empty_output`
- `script_deviation`

---

## `turn_grades.jsonl`

One object per Ninereeds answer turn:

```json
{
  "turn_id": "t006",
  "prompt": "Is a cat a dog?",
  "ninereeds_answer": "A cat is an animal. A dog is an animal. A cat is a dog.",
  "grade": "pass|partial|fail|ungradable",
  "on_topic": true,
  "malformed": false,
  "failure_modes": ["same_category_confusion"],
  "required_hits": ["cat", "animal", "dog"],
  "required_misses": ["not a dog"],
  "forbidden_hits": ["cat is a dog"],
  "eligible_for_training": false,
  "suggested_correction": "A cat is an animal. A dog is an animal. A cat is not a dog."
}
```

---

## `proposed_training.jsonl`

DeepSeek writes grading-validated proposed turns here. These are not approved for weight
updates until the orchestrator copies accepted records into an update buffer as
`approved_training.jsonl`.

```json
{
  "schema_version": "msm_training_turn_v1",
  "session_id": "string",
  "concept": "cat",
  "card_id": "cat_boundary_l1",
  "turn_id": "t006_repair",
  "prompt": "[user]Is a cat a dog?\n[Ninereeds]",
  "training_answer": "A cat is an animal. A dog is an animal. A cat is not a dog.",
  "source": "deepseek_proposed_correction",
  "target_failure": "same_category_confusion",
  "deepseek_validated": true,
  "orchestrator_approved": false
}
```

Wrong Ninereeds answers must not appear in this file.
