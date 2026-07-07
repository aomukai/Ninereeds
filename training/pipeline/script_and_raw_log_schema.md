# MSM Script And Raw Log Schemas

This contract defines the executor-to-trainer boundary.

Machine-readable schemas:

- `training/pipeline/script_schema.json`
- `training/pipeline/raw_chat_line_schema.json`

---

## `script.json`

The executor writes one `script.json` per script execution. The trainer treats it as a
fixed instruction file, not as a plan to interpret.

Minimal example:

```json
{
  "schema_version": "msm_script_v1",
  "script_id": "scr_dog_cat_001",
  "session_id": "session_dog_cat_001",
  "orchestrator_plan_id": "plan_animals_001",
  "script_author": "executor:qwen3.6-36b-a3b",
  "created_at": "2026-07-08T00:00:00Z",
  "concept": "dog",
  "card_id": "dog_boundary_l1",
  "checkpoint": "core/c17_contrast_angle_1200_e4.pt",
  "session_mode": "contrast_session",
  "intended_stage": "or_question",
  "intended_failure_targets": ["same_category_confusion"],
  "trainer_contract": {
    "send_user_prompt": true,
    "record_original_answer": true,
    "send_teacher_correction": true,
    "record_after_correction_answer": true,
    "do_not_grade": true,
    "do_not_modify_items": true
  },
  "items": [
    {
      "item_id": "i001",
      "stage": "or_question",
      "user_prompt": "Is a dog a cat?",
      "teacher_correction": "A dog is not a cat.",
      "ask_after_correction": true,
      "expected_original": {
        "acceptable": ["A dog is not a cat."],
        "forbidden": ["dog is a cat"]
      },
      "expected_after_correction": {
        "acceptable": ["A dog is not a cat."],
        "forbidden": ["dog is a cat"]
      },
      "required_hits": ["dog", "cat"],
      "forbidden_hits": ["dog is a cat"],
      "target_failure_modes": ["same_category_confusion"],
      "training_answer_max_bytes": 96,
      "notes": null
    }
  ]
}
```

Trainer rules:

- send `user_prompt` exactly
- record the original Ninereeds answer
- emit `teacher_correction` exactly when non-null
- record a post-correction Ninereeds answer only when `ask_after_correction` is true
- never grade
- never rewrite prompts or corrections

---

## `raw_chat.jsonl`

The trainer writes one JSON object per event. The file is append-only for the session.

Example lines for one script item:

```json
{"schema_version":"msm_raw_chat_line_v1","session_id":"session_dog_cat_001","script_id":"scr_dog_cat_001","item_id":"i001","sequence_index":0,"event_type":"user_prompt","speaker":"user","text":"Is a dog a cat?","created_at":"2026-07-08T00:00:01Z","latency_ms":null,"checkpoint":"core/c17_contrast_angle_1200_e4.pt","inference":null,"error":null}
{"schema_version":"msm_raw_chat_line_v1","session_id":"session_dog_cat_001","script_id":"scr_dog_cat_001","item_id":"i001","sequence_index":1,"event_type":"ninereeds_original_answer","speaker":"ninereeds","text":"A dog is an animal. A cat is an animal. A dog is a cat.","created_at":"2026-07-08T00:00:02Z","latency_ms":820,"checkpoint":"core/c17_contrast_angle_1200_e4.pt","inference":{"temperature":0.0,"top_k":1,"max_new_tokens":96,"device":"cuda"},"error":null}
{"schema_version":"msm_raw_chat_line_v1","session_id":"session_dog_cat_001","script_id":"scr_dog_cat_001","item_id":"i001","sequence_index":2,"event_type":"teacher_correction","speaker":"teacher","text":"A dog is not a cat.","created_at":"2026-07-08T00:00:03Z","latency_ms":null,"checkpoint":"core/c17_contrast_angle_1200_e4.pt","inference":null,"error":null}
{"schema_version":"msm_raw_chat_line_v1","session_id":"session_dog_cat_001","script_id":"scr_dog_cat_001","item_id":"i001","sequence_index":3,"event_type":"ninereeds_after_correction_answer","speaker":"ninereeds","text":"A dog is not a cat.","created_at":"2026-07-08T00:00:04Z","latency_ms":610,"checkpoint":"core/c17_contrast_angle_1200_e4.pt","inference":{"temperature":0.0,"top_k":1,"max_new_tokens":96,"device":"cuda"},"error":null}
```

Execution errors are logged as `event_type: "execution_error"` with `speaker: "trainer"`
and an `error` object. The executor may reject or escalate a session if the raw log is
missing required events for any item.

---

## Event Ordering

For each `item_id`, expected order is:

1. `user_prompt`
2. `ninereeds_original_answer`
3. `teacher_correction`, when `teacher_correction` in `script.json` is not null
4. `ninereeds_after_correction_answer`, when `ask_after_correction` is true

The `sequence_index` field is global within the session and starts at `0`.
