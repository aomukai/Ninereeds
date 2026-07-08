# Ninereeds — Session Index

Read this after `CLAUDE.md`. This file is the short map for a fresh session.

Last updated: 2026-07-09

---

## Session Startup

1. Read `CLAUDE.md` for global operating constraints.
2. Read this file for current artifact pointers and key references.
3. Read `todo.md` for the active work queue.
4. Run Step 0 from `training/pipeline/runbook.md` to check MSM session/update state.

---

## Current State

| Field | Value |
|---|---|
| Active regime | Cold-start MSM developmental training |
| Canonical runbook | `training/pipeline/runbook.md` |
| Active phase | `phase_0_form` in `training/pipeline/msm/state/phase_registry.json` |
| Initial checkpoint policy | Start from `scratch` unless a phase transition artifact says otherwise |
| Active work | Build the stateless cold-start MSM phase pipeline and supporting scripts |
| Update backend | `meta/scripts/msm_micro_update.py` |
| Hardware status | Training machine not assembled yet; implementation can proceed, live runs wait |

Historical campaign checkpoints are evidence only. They are not active parents.

---

## Stateless Pipeline Rule

Pipeline programs should not carry hidden memory between runs. Every runner reads explicit
input artifacts, writes explicit output artifacts, and can be restarted from disk.

Durable facts live in JSON/report artifacts under `training/pipeline/msm/`, especially:

- `state/phase_registry.json` - active phase and canonical phase order
- `phase_blocks/PHASE_ID/BLOCK_ID/block_report.json` - cold-start block evidence
- `sessions/SESSION_ID/report_card.json` - later MSM session evidence
- `state/concept_state.json` and `state/session_archive.json` - derived indexes when used

If an artifact can be reconstructed from reports, treat it as a cache/index, not hidden
authority. When artifacts disagree, prefer the immutable source report over a derived
summary.

---

## Active Pipeline References

| What | Where |
|---|---|
| Orchestrator startup | `training/pipeline/orchestrator_startup.md` |
| Executable step sequence | `training/pipeline/runbook.md` |
| MSM training doctrine | `training/pipeline/training.md` |
| Cold-start phase ladder | `training/pipeline/cold_start_phases.md` |
| Pipeline/dataflow map | `training/pipeline/pipeline.md` |
| Session/update decision semantics | `training/pipeline/iteration_schema.md` |
| Mommy Says system boundary | `training/pipeline/mommy_says_machine.md` |
| Concept-card tutor method | `training/pipeline/tutor_loop.md` |
| Sentinel files | `training/pipeline/sentinel_files.md` |
| MSM config contract | `training/pipeline/msm_config.md` |
| Codex brake/status schemas | `training/pipeline/codex_brake_schema.json` + `training/pipeline/codex_status_schema.json` |
| Auto-advance schemas | `training/pipeline/active_campaign_policy_schema.json`, `training/pipeline/word_queue_schema.json`, `training/pipeline/auto_advance_state_schema.json` |
| Session report schema | `training/pipeline/session_report_schema.md` + `.json` |
| Training turn schema | `training/pipeline/training_turn_schema.json` |
| Cold-start phase schema | `training/pipeline/cold_start_phase_schema.json` |
| Phase registry schema | `training/pipeline/phase_registry_schema.json` |
| Phase block report schema | `training/pipeline/phase_block_report_schema.json` |
| Active phase registry | `training/pipeline/msm/state/phase_registry.json` |
| Concept state schema | `training/pipeline/concept_state_schema.json` |
| Session archive schema | `training/pipeline/session_archive_schema.json` |
| Update artifact schema | `training/pipeline/update_artifact_schema.md` |
| Update manifest schema | `training/pipeline/update_manifest_schema.json` |
| Update candidate eval schema | `training/pipeline/update_candidate_eval_schema.json` |
| Orchestrator config schema | `training/pipeline/orchestrator_config_schema.json` |
| Micro-update backend | `meta/scripts/msm_micro_update.py` |
| Cold-start phase runner | `meta/scripts/msm_phase_runner.py` |
| Orchestrator status helper | `meta/scripts/msm_orchestrator_status.py` |
| MSM utility helpers | `meta/scripts/msm_pipeline_utils.py` |
| Codex status watchdog | `meta/scripts/watch_codex_status.py` |

---

## Historical References

| What | Where |
|---|---|
| Archived corpus inventory and campaign history | `archive/training_pipeline/curriculum_topology.md` |
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
training/pipeline/       active MSM docs, schemas, and explicit artifacts
training/pipeline/msm/   artifact tree: state files, phase blocks, sessions, buffers, updates, logs
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
