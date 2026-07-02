# Ninereeds — Session Index

Read this after `CLAUDE.md`. This file is the short map for a fresh session.

Last updated: 2026-07-01

---

## Session Startup

1. Read `CLAUDE.md` for global operating constraints.
2. Read this file for current state and key pointers.
3. Read `todo.md` for the active work queue.
4. Run Step 0 from `training/pipeline/runbook.md` to check MSM session/update state.

---

## Current State

| Field | Value |
|---|---|
| Active regime | MSM session training, not broad corpus pretraining |
| Canonical runbook | `training/pipeline/runbook.md` |
| Protected baseline | `core/c17_contrast_angle_1200_e4.pt` |
| Latest closed campaign | C17 — kernel corpus and chat-capable core exploration |
| Best C17 signal | Contrast-angle 1,200-concept run: default eval 5/7, avg 0.905 |
| Active work | Build the concept-card MSM pipeline and supporting scripts |
| Update backend | `meta/scripts/msm_micro_update.py` |
| Hardware status | Training machine not assembled yet; implementation can proceed, live runs wait |

Do not continue from C17 repair branches unless an explicit recovery experiment says so.

---

## Active Pipeline References

| What | Where |
|---|---|
| Executable step sequence | `training/pipeline/runbook.md` |
| MSM training doctrine | `training/pipeline/training.md` |
| Pipeline/dataflow map | `training/pipeline/pipeline.md` |
| Session/update decision semantics | `training/pipeline/iteration_schema.md` |
| Mommy Says system boundary | `training/pipeline/mommy_says_machine.md` |
| Concept-card tutor method | `training/pipeline/tutor_loop.md` |
| Sentinel files | `training/pipeline/sentinel_files.md` |
| MSM config contract | `training/pipeline/msm_config.md` |
| Session report schema | `training/pipeline/session_report_schema.md` + `.json` |
| Training turn schema | `training/pipeline/training_turn_schema.json` |
| Update artifact schema | `training/pipeline/update_artifact_schema.md` |
| Update manifest schema | `training/pipeline/update_manifest_schema.json` |
| Update candidate eval schema | `training/pipeline/update_candidate_eval_schema.json` |
| Orchestrator config schema | `training/pipeline/orchestrator_config_schema.json` |
| Micro-update backend | `meta/scripts/msm_micro_update.py` |

---

## Historical References

| What | Where |
|---|---|
| C17 handoff | `training/logs/campaign_17_reports/01_handoff.md` |
| Archived corpus inventory and campaign history | `archive/training_pipeline/curriculum_topology.md` |
| Archived C17 epoch-campaign configs | `archive/training_pipeline/epoch_campaigns/` |
| Kernel spec | `kernel.md` |
| Identity spec | `identity.md` |
| Kernel file format | `training/corpus_admin/kernel/FORMAT.md` |
| Completed work log | `history.md` |

---

## Diagnostics

| Tool | Notes |
|---|---|
| Brain map | `meta/scripts/brain_map.py probe` -> `hubs` -> `graph`; outputs in `training/logs/brain_maps/` |
| Brain trace | Generate/validate probes, then trace; read `training/logs/brain_maps/<name>_trace_report.md` |
| Grounding eval | `meta/scripts/eval_grounding.py` |
| Manual greedy gate | See current MSM runbook/report-card flow before using directly |

Evaluation is anytime in the MSM regime. It is not tied to epochs.

---

## Project Layout

```text
training/pipeline/       active MSM docs and schemas only
training/msm/            planned runtime state: sessions, buffers, updates, logs
meta/scripts/            runners, generators, eval tools, MSM micro-update backend
core/                    local working checkpoints
checkpoints/             promoted checkpoints
training/logs/           historical campaign logs, grounding evals, brain maps
training_data/           historical/generated corpus sources
archive/training_pipeline/ historical epoch-campaign pipeline docs/configs
```

---

## Platform

- Python for training: `/home/aomukai/.unsloth/studio/unsloth_studio/bin/python`
- Training GPU: `CUDA_VISIBLE_DEVICES=0`
- Chat/executor GPU target: second RTX 3060 once the new machine exists
- Model: `bdh.py`; do not modify casually
- Checkpoints: `core/*.pt` and `checkpoints/` are local-only

`train.py` has a legacy `training_activation_audit.md` gate. MSM micro-updates bypass it
through `meta/scripts/msm_micro_update.py` after manifest and approved-turn validation.
