# MSM Update Artifact Schemas

Session reports describe evidence. Update artifacts describe weight-changing events.

The active update backend is a placeholder contract named:

```bash
python3 meta/scripts/msm_micro_update.py --manifest training/msm/updates/UPDATE_ID/update_manifest.json
```

If `meta/scripts/msm_micro_update.py` does not exist yet, the orchestrator must create
`BLOCKED` or request implementation. Do not improvise another update path in a cold
session.

V1 uses `train.py` under the hood. It runs one sequential JSONL pass and treats
`update_backend.max_steps` as an upper bound on train.py micro-batches. If the approved
turn count cannot fit that bound within the backend's maximum safe batch size, the backend
fails before training.

The legacy `training_activation_audit.md` gate in `train.py` is bypassed for MSM updates
with `--skip-training-audit`. The MSM wrapper replaces that broad campaign-era gate with
manifest validation, approved-turn validation, line-count checks, and protected-anchor
post-update evaluation.

`update_backend.command` is checked by the backend: it must invoke
`meta/scripts/msm_micro_update.py` and its `--manifest` path must match the manifest being
executed. The backend also writes the actual argv to `backend_command.json` and the
generated train.py command to `train_command.json`.

The backend refuses to overwrite an existing `output_checkpoint` by default. Use
`--allow-overwrite` only after an explicit orchestrator decision.

Machine-readable schemas:

- `training/pipeline/update_manifest_schema.json`
- `training/pipeline/update_candidate_eval_schema.json`
- `training/pipeline/training_turn_schema.json`

---

## `update_manifest.json`

Written before an update runs.

An `update_manifest.json` must not be written if the approved buffer contains zero records.
That is a no-op decision, not `BLOCKED`.
Every record in `approved_training.jsonl` must validate against
`training/pipeline/training_turn_schema.json` and have `orchestrator_approved: true`.
`approved_turn_count` must equal the total line count of all referenced
`approved_training.jsonl` files.

```json
{
  "schema_version": "msm_update_manifest_v1",
  "update_id": "upd_000001_cat_boundary",
  "created_at": "2026-07-01T00:00:00Z",
  "parent_checkpoint": "core/c17_contrast_angle_1200_e4.pt",
  "output_checkpoint": "core/msm/upd_000001_cat_boundary.pt",
  "source_sessions": ["session_cat_001"],
  "approved_training_files": [
    "training/msm/buffers/buf_000001/approved_training.jsonl"
  ],
  "approved_turn_count": 5,
  "approval": {
    "orchestrator_approved": true,
    "approved_by": "orchestrator_id",
    "approval_reason": "Repair cat_not_dog after report card evidence.",
    "human_approved": false
  },
  "update_backend": {
    "name": "buffered_micro_update",
    "command": "python3 meta/scripts/msm_micro_update.py --manifest training/msm/updates/upd_000001_cat_boundary/update_manifest.json",
    "learning_rate": 0.00002,
    "max_steps": 1,
    "notes": "Backend implementation TBD."
  },
  "target_axes": ["cat_not_dog"],
  "protected_anchors_required": true
}
```

---

## `update_candidate_eval.json`

Written after the update candidate is evaluated.

```json
{
  "schema_version": "msm_update_candidate_eval_v1",
  "update_id": "upd_000001_cat_boundary",
  "candidate_checkpoint": "core/msm/upd_000001_cat_boundary.pt",
  "parent_checkpoint": "core/c17_contrast_angle_1200_e4.pt",
  "target_checks": {
    "passed": true,
    "summary": "cat_not_dog repaired in scripted probes",
    "report_cards": ["training/msm/sessions/session_cat_replay_001/report_card.json"]
  },
  "protected_anchor_checks": {
    "tested": true,
    "passed": true,
    "failures": []
  },
  "quality_checks": {
    "malformed_rate_ok": true,
    "repetition_rate_ok": true,
    "script_deviation": false
  },
  "decision": {
    "status": "accepted|rejected|manual_review",
    "reason": "short reason",
    "promoted_checkpoint": "checkpoints/msm_current_best.pt"
  }
}
```
