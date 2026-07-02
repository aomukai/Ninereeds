# MSM Iteration Schema

Each iteration is one bounded session or one bounded micro-update decision.
For executable step order, use `runbook.md`; this file defines decision semantics.

---

## State

- `protected_best`: checkpoint that must not be damaged. Current baseline:
  `core/c17_contrast_angle_1200_e4.pt`.
- `update_candidate`: checkpoint produced by an optional MSM micro-update. This is not
  an epoch-campaign branch; it exists only until accepted or rejected by gates.
- `session`: one word/card chat run.
- `report_card`: DeepSeek's structured report for the session.
- `concept_state`: persistent state for the card.
- `protected_anchor_gate`: identity, unknown-boundary, and permanent anchor checks.

---

## Session Loop

1. Start from `protected_best` or last accepted checkpoint.
2. Select one concept card and one objective.
3. DeepSeek writes a fixed script.
4. Gemma executes the script and writes a raw log.
5. DeepSeek fills the report card.
6. Orchestrator decides:
   - accept evidence and schedule next card
   - replay same card with a repair script
   - request adaptive DeepSeek session
   - run eval or brain scan
   - approve proposed training turns into a buffer
   - apply micro-update
   - escalate to user

---

## Micro-Update Loop

1. Gather orchestrator-approved turns only.
2. Write update manifest with source session IDs.
3. Apply one small update from the chosen parent checkpoint.
4. Run target checks and protected-anchor checks.
5. Decide:
   - keep update candidate if target improves and protected anchors pass
   - reject update candidate if protected anchors regress
   - rollback and replay if a specific repair is indicated
   - ask user if automation is blocked

---

## Default Gates

Promotion requires:

- report card complete
- no Gemma script deviation
- target axis improved or intentionally stable
- protected anchors pass
- malformed/repetition rates below configured limits
- no high-severity new failure

Threshold values come from `training/msm/state/orchestrator_config.json`; the required
config shape is documented in `msm_config.md`.

Rollback is required when:

- identity or unknown-boundary anchors regress
- harmful equivalence appears and persists
- raw log is malformed enough that grading is unreliable
- proposed or approved turns cannot be extracted safely

---

## Repair Dose Rules

- repair one failure type at a time
- prefer short staged correction turns
- use one sibling contrast per turn
- close with a compact positive consolidation
- do not train from the wrong answer
- do not add free-practice material to the update buffer

## Buffer Rule

DeepSeek writes `proposed_training.jsonl`. The orchestrator creates
`training/msm/buffers/BUFFER_ID/approved_training.jsonl` by selecting records from one
or more proposal files. A micro-update may run when the configured buffer policy is met
or when the orchestrator explicitly approves a single-session repair update.

---

## Brain Scan Rule

Run a brain scan when chat reports show a stable confusion but do not explain the route:

- same-category identity confusion
- cross-category bleed
- protected anchor routed through fragile hubs
- repair works in one prompt form but fails nearby forms

Brain scans diagnose routing. They do not promote update candidates by themselves.
