# Archived Epoch Campaign Files

These files belong to the C17-era campaign runner workflow:

`corpus/jsonl -> fixed training epochs -> eval/manual gate -> compare checkpoints`

That workflow is historical infrastructure as of 2026-07-01. The active training regime
is MSM session training, documented in:

- `training/pipeline/training.md`
- `training/pipeline/pipeline.md`
- `training/pipeline/runbook.md`
- `training/pipeline/session_report_schema.md`

Keep these files for reproducibility and comparison experiments. Do not treat them as
active configs unless the orchestrator explicitly chooses an epoch-campaign experiment.
