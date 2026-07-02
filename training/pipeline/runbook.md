# MSM Runbook

Open this document when running or supervising the active training loop.

---

## Step 0 — Orient

Check for active sessions, pending reports, and human-attention sentinels.

```bash
ps aux | grep -E "gemma|ninereeds|chat" | grep -v grep
find training/msm \( \
  -name HUMAN_ATTENTION \
  -o -name BLOCKED \
  -o -name TRAINING_MACHINE_DOWN \
  -o -name API_CREDITS_EXHAUSTED \
  -o -name PROMOTION_REVIEW_REQUIRED \
\) 2>/dev/null
find training/msm/sessions -maxdepth 2 -name report_card.json 2>/dev/null | tail -20
```

States:

- **Session running** — monitor, do not launch another session for the same card.
- **Raw log exists, report missing** — task DeepSeek to write the report card.
- **Report exists, decision missing** — orchestrator reads the report and writes next plan.
- **Human sentinel exists** — Hermes pings the user; wait for manual resolution.

---

## Step 1 — Read Current State

Read:

- latest orchestrator log
- latest `report_card.json` for the target concept
- concept state JSON
- protected-anchor status
- parent checkpoint metadata

Do not plan from memory. The JSON artifacts are the source of truth.

---

## Step 2 — Choose One Session Objective

Choose one card and one objective:

- teach a new positive anchor
- test recall
- repair a specific failure
- add one contrast
- test a protected anchor
- run a brain scan because chat evidence is inconclusive

One session should not combine multiple unrelated objectives.

---

## Step 3 — Write Orchestrator Plan

The orchestrator writes a bounded plan for DeepSeek:

- concept/card
- parent checkpoint
- session mode
- target axes
- failure modes to test
- forbidden scope
- whether proposed training turns may be extracted
- whether a micro-update is allowed after the report

If the plan needs human input, write the configured sentinel file and stop.

---

## Step 4 — DeepSeek Builds Script

DeepSeek writes `script.json`.

Script requirements:

- fixed ordered prompts
- no Gemma discretion
- correction turns written exactly
- expected answer metadata where useful
- stop conditions for execution errors only
- script ID and orchestrator plan ID

Gemma must be able to execute the script without interpreting the research goal.

---

## Step 5 — Gemma Executes

Gemma runs the script against Ninereeds and writes `raw_chat.jsonl`.

Gemma records:

- turn ID
- prompt
- Ninereeds raw output
- timestamp
- execution error, if any

Gemma does not grade or summarize.

---

## Step 6 — DeepSeek Reports

DeepSeek reads `raw_chat.jsonl` and writes:

- `turn_grades.jsonl`
- `report_card.json`
- `report.md`
- `proposed_training.jsonl` if proposed training turns exist
- `failed_turns.jsonl`

DeepSeek may recommend a next local action, but the orchestrator decides.

---

## Step 7 — Orchestrator Decides

Possible decisions:

- accept session evidence and update concept state
- run another scripted session
- rollback and replay with repair
- request DeepSeek adaptive session
- run protected anchors
- run grounding eval
- run brain map
- apply buffered micro-update
- reject session as unusable
- escalate to user through Hermes

Record the decision in a stable JSON artifact.

---

## Step 8 — Optional Micro-Update

If allowed:

1. Confirm `proposed_training.jsonl` exists if DeepSeek proposed trainable turns.
2. Confirm the orchestrator copied accepted records into `approved_training.jsonl`.
3. Confirm every proposed/approved turn validates against `training_turn_schema.json`.
4. Confirm approved turn count meets `min_approved_turns_for_update`.
5. Confirm `approved_turn_count` equals the line count of every referenced
   `approved_training.jsonl` file combined.
6. Confirm parent checkpoint is correct.
7. Confirm `output_checkpoint` does not already exist, unless an explicit overwrite
   decision has been recorded.
8. Write `update_manifest.json`.
9. Run the micro-update backend command from `update_artifact_schema.md`.
10. Write `update_candidate_eval.json`.
11. Accept or reject the update candidate.

Never update from raw chat logs.
Buffer policy and quality thresholds are documented in `msm_config.md`.
The MSM backend intentionally passes `--skip-training-audit` to `train.py`; do not remove
that unless the MSM manifest/update gates are replaced by a stronger equivalent.

---

## Step 9 — Hermes Notification

Hermes reports:

- session completed
- report card summary
- accepted/rejected update candidate
- blocked state
- human attention required

Hermes pings the user when a sentinel file exists or when configured thresholds are crossed.

Sentinel contract: `training/pipeline/sentinel_files.md`.

---

## Current Protected Baseline

`core/c17_contrast_angle_1200_e4.pt`

Do not continue from C17 repair branches unless the orchestrator explicitly chooses a
recovery experiment.
