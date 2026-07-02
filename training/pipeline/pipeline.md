# MSM Pipeline

Design reference for the active autonomous training pipeline.

Last updated: 2026-07-01

---

## Pipeline Shape

```text
orchestrator plan
  -> DeepSeek script generation
  -> Gemma fixed-script execution
  -> raw chat log
  -> DeepSeek report card
  -> orchestrator decision
  -> optional micro-update / probe / replay / scan / escalation
```

The active loop is session-based and epochless. One word/card session is the smallest
unit of evidence.

---

## Directories

Planned active layout:

```text
training/msm/
  state/
    concept_state.json
    protected_anchors.json
    orchestrator_state.json
    orchestrator_config.json
  plans/
    PLAN_ID.json
  sessions/
    SESSION_ID/
      script.json
      raw_chat.jsonl
      turn_grades.jsonl
      report_card.json
      report.md
      proposed_training.jsonl
      failed_turns.jsonl
  buffers/
    BUFFER_ID/
      approved_training.jsonl
  updates/
    UPDATE_ID/
      update_manifest.json
      source_sessions.txt
      update_candidate_eval.json
  logs/
    orchestrator.jsonl
    hermes.jsonl
```

Existing historical campaign logs remain under `training/logs/`.

---

## Components

### Orchestrator

Reads report cards and state, chooses the next action, and writes plans.

Required outputs:

- plan JSON
- decision JSON
- human-attention sentinel when blocked

### DeepSeek Executor

Tactical worker. Converts plans into scripts, reads raw logs, fills reports, and extracts
proposed training turns.

Required outputs:

- `script.json`
- `report_card.json`
- `turn_grades.jsonl`
- optional `proposed_training.jsonl`

### Gemma Worker

Mechanical runner. Executes fixed scripts only.

Required outputs:

- `raw_chat.jsonl`
- execution status

### Hermes

Notification and watchdog layer. Posts Discord reports and pings the user when a sentinel
file appears.

---

## Session Lifecycle

The canonical executable step sequence is `runbook.md`. This lifecycle is a design map,
not a second runbook.

1. **Plan** — orchestrator selects concept, objective, mode, and limits.
2. **Script** — DeepSeek writes exact prompt/correction sequence.
3. **Execute** — Gemma runs script against Ninereeds.
4. **Report** — DeepSeek grades and summarizes with fixed schema.
5. **Decide** — orchestrator chooses accept, replay, repair, update, eval, scan, or escalate.
6. **Update** — optional buffered micro-update from orchestrator-approved turns only.
7. **Gate** — protected anchors and target checks determine promotion.

---

## Sentinel Files

Canonical names are defined in `sentinel_files.md`:

- `HUMAN_ATTENTION` — user action required
- `BLOCKED` — automation cannot continue safely
- `TRAINING_MACHINE_DOWN` — local runner unavailable
- `API_CREDITS_EXHAUSTED` — paid API worker cannot continue
- `PROMOTION_REVIEW_REQUIRED` — update candidate needs manual approval

Hermes watches for sentinel files and pings the user.

---

## Update Backend

Initial implementation: buffered micro-updates.

Invocation contract:

```bash
python3 meta/scripts/msm_micro_update.py --manifest training/msm/updates/UPDATE_ID/update_manifest.json
```

If that script does not exist yet, the orchestrator must write `BLOCKED` and request
implementation. Update artifact schemas are defined in `update_artifact_schema.md`.
Thresholds and buffer triggers are defined by `msm_config.md`.

The rest of the pipeline must treat update execution as a backend. Later backends may
support true online Hebbian updates, but logs, report cards, and orchestrator decisions
should not depend on that implementation detail.

---

## Deprecated Pipeline

The old campaign runner flow trained corpus files for fixed epoch counts and selected
winners from eval/brain-map metrics. That flow is archived as historical infrastructure.

Use it only for explicit comparison experiments.
