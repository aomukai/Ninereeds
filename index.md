# Ninereeds — Session Index

Read this after `CLAUDE.md`. This file is the short map for a fresh session.

Last updated: 2026-07-10

---

## Session Startup

1. Read `CLAUDE.md` for global operating constraints.
2. Read this file for current artifact pointers and key references.
3. Read `todo.md` for the active work queue.
4. Run `training/pipeline/start.sh --status-only` for the deterministic MSM startup summary.
5. Run Step 0 from `training/pipeline/runbook.md` when planning or supervising MSM work.

---

## Current State

| Field | Value |
|---|---|
| Active regime | Cold-start MSM developmental training |
| Canonical runbook | `training/pipeline/runbook.md` |
| Active phase | `phase_0_form` in `training/pipeline/msm/state/phase_registry.json` |
| Initial checkpoint policy | `training/pipeline/msm/state/orchestrator_config.json` starts from `scratch`; Phase 0/1 local blocks advance `checkpoint_policy.current_parent` after successful probe reports |
| Active work | Assemble training machine, then configure concrete SSH/trainbox handoff and tune the two-PC loop |
| Update backend | `meta/scripts/msm_micro_update.py` |
| Startup entrypoint | `training/pipeline/start.sh` |
| Hermes setup contract | `training/pipeline/hermes.md` |
| Hardware status | Training machine not assembled yet; local bootstrap/status tooling is ready, concrete SSH config waits |

Historical campaign checkpoints are evidence only. They are not active parents.

---

## Stateless Pipeline Rule

Pipeline programs should not carry hidden memory between runs. Every runner reads explicit
input artifacts, writes explicit output artifacts, and can be restarted from disk.

Durable facts live in JSON/report artifacts under `training/pipeline/msm/`, especially:

- `state/phase_registry.json` - active phase and canonical phase order
- `state/orchestrator_config.json` - current parent/config defaults
- `state/orchestrator_status.json` and `.md` - orchestrator state-of-the-union for Hermes
- `state/hermes_digest.md` - compact Hermes Discord digest source
- `phase_blocks/PHASE_ID/BLOCK_ID/block_report.json` - cold-start block evidence
- `phase_blocks/PHASE_ID/BLOCK_ID/probe_results.jsonl` - cold-start probe outputs
- `sessions/SESSION_ID/report_card.json` - later MSM session evidence
- `state/concept_state.json` and `state/session_archive.json` - derived indexes when used

If an artifact can be reconstructed from reports, treat it as a cache/index, not hidden
authority. When artifacts disagree, prefer the immutable source report over a derived
summary.

---

## Active Pipeline References

| What | Where |
|---|---|
| Startup/supervisor entrypoint | `training/pipeline/start.sh` |
| Orchestrator startup | `training/pipeline/orchestrator_startup.md` |
| Executable step sequence | `training/pipeline/runbook.md` |
| MSM training doctrine | `training/pipeline/training.md` |
| Cold-start phase ladder | `training/pipeline/cold_start_phases.md` |
| Pipeline/dataflow map | `training/pipeline/pipeline.md` |
| Session/update decision semantics | `training/pipeline/iteration_schema.md` |
| Mommy Says system boundary | `training/pipeline/mommy_says_machine.md` |
| Concept-card tutor method | `training/pipeline/tutor_loop.md` |
| Sentinel files | `training/pipeline/sentinel_files.md` |
| Hermes setup contract | `training/pipeline/hermes.md` |
| MSM config contract | `training/pipeline/msm_config.md` |
| Codex brake/status schemas | `training/pipeline/codex_brake_schema.json` + `training/pipeline/codex_status_schema.json` |
| Auto-advance schemas | `training/pipeline/active_campaign_policy_schema.json`, `training/pipeline/word_queue_schema.json`, `training/pipeline/auto_advance_state_schema.json` |
| Session report schema | `training/pipeline/session_report_schema.md` + `.json` |
| Training turn schema | `training/pipeline/training_turn_schema.json` |
| Cold-start phase schema | `training/pipeline/cold_start_phase_schema.json` |
| Phase registry schema | `training/pipeline/phase_registry_schema.json` |
| Phase block report schema | `training/pipeline/phase_block_report_schema.json` |
| Active phase registry | `training/pipeline/msm/state/phase_registry.json` |
| Active orchestrator config | `training/pipeline/msm/state/orchestrator_config.json` |
| Orchestrator status artifacts | `training/pipeline/msm/state/orchestrator_status.json` + `.md` |
| Hermes digest artifact | `training/pipeline/msm/state/hermes_digest.md` |
| Concept state schema | `training/pipeline/concept_state_schema.json` |
| Session archive schema | `training/pipeline/session_archive_schema.json` |
| Update artifact schema | `training/pipeline/update_artifact_schema.md` |
| Update manifest schema | `training/pipeline/update_manifest_schema.json` |
| Update candidate eval schema | `training/pipeline/update_candidate_eval_schema.json` |
| Orchestrator config schema | `training/pipeline/orchestrator_config_schema.json` |
| Micro-update backend | `meta/scripts/msm_micro_update.py` |
| Config bootstrap helper | `meta/scripts/msm_bootstrap_config.py` |
| Cold-start phase runner | `meta/scripts/msm_phase_runner.py` |
| Orchestrator status helper | `meta/scripts/msm_orchestrator_status.py` |
| Hermes digest builder | `meta/scripts/hermes_digest.py` |
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
meta/scripts/            runners, generators, eval tools, status/digest helpers, MSM micro-update backend
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
- Two-PC target: Hermes/watchdog/orchestrator status on the main machine; executor/trainer on trainbox after concrete SSH paths are configured
- Model: `bdh.py`; do not modify casually
- Checkpoints: `core/*.pt` and `checkpoints/` are local-only

`train.py` has a legacy `training_activation_audit.md` gate. MSM micro-updates bypass it
through `meta/scripts/msm_micro_update.py` after manifest and approved-turn validation.
