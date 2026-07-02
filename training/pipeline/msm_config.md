# MSM Configuration Contract

The active config file should live at:

`training/msm/state/orchestrator_config.json`

Machine-readable schema:

`training/pipeline/orchestrator_config_schema.json`

If the file does not exist yet, the orchestrator should create it from this contract before
running autonomous sessions.

---

## Required Fields

```json
{
  "schema_version": "msm_orchestrator_config_v1",
  "protected_best": "core/c17_contrast_angle_1200_e4.pt",
  "thresholds": {
    "max_malformed_rate": 0.10,
    "max_repetition_collapse": 0,
    "max_empty_or_near_empty_rate": 0.10
  },
  "buffer_policy": {
    "min_proposed_turns_for_update": 5,
    "min_approved_turns_for_update": 1,
    "max_sessions_per_buffer": 5,
    "allow_single_session_repair_update": true
  },
  "sentinel_contract": "training/pipeline/sentinel_files.md",
  "codex_status_schema": "training/pipeline/codex_status_schema.json",
  "codex_brake_schema": "training/pipeline/codex_brake_schema.json",
  "active_campaign_policy_schema": "training/pipeline/active_campaign_policy_schema.json",
  "word_queue_schema": "training/pipeline/word_queue_schema.json",
  "auto_advance_state_schema": "training/pipeline/auto_advance_state_schema.json",
  "update_manifest_schema": "training/pipeline/update_manifest_schema.json",
  "update_candidate_eval_schema": "training/pipeline/update_candidate_eval_schema.json"
}
```

Thresholds are starting defaults, not research findings. The orchestrator may change them
only by writing an explicit decision artifact.

---

## Buffer Location

Approved buffers live under:

`training/msm/buffers/BUFFER_ID/approved_training.jsonl`

DeepSeek never writes this file directly. The orchestrator creates it by selecting records
from one or more `proposed_training.jsonl` files.

An update manifest must not be written unless the approved buffer contains at least
`min_approved_turns_for_update` records.
