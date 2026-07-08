# MSM Iteration Schema

Each iteration is one bounded script execution, one executor auto-advance decision, or one
bounded micro-update decision. For executable step order, use `runbook.md`; this file
defines decision semantics.

---

## State

- `checkpoint_policy`: current parent policy. Cold-start begins from `scratch`; later
  phases may use accepted cold-start checkpoints.
- `update_candidate`: checkpoint produced by an optional MSM micro-update. This is not
  an epoch-campaign branch; it exists only until accepted or rejected by gates.
- `session`: one word/card scripted run.
- `script`: one executor-authored set of prompts/corrections for the trainer.
- `report_card`: executor's structured report for the session.
- `concept_state`: persistent state for the card.
- `session_archive`: queryable index of accepted session summaries and fingerprints.
- `protected_anchor_gate`: identity, unknown-boundary, and permanent anchor checks.

---

## Script Loop

1. Start from `scratch` or the current accepted cold-start checkpoint.
2. Select the next concept card from the word queue.
3. Executor writes one fixed script under the active policy.
   - select the executor through the fixed v1 selector
   - include scratchpad context only when the config flag allows it
   - compute the deterministic script fingerprint
   - reject exact structural duplicates unless policy explicitly allows repetition
4. Trainer executes the script and writes a raw log.
5. Executor grades every scripted item:
   - original answer status
   - on-topic/off-topic
   - post-correction status when present
6. Executor decides whether policy allows another local script.
7. Executor escalates to the orchestrator when stop conditions fire.

---

## Executor Auto-Advance Decision

Executor may continue locally when:

- at least one scripted item has a correct original answer or correct post-correction answer
- all answers are on-topic
- malformed/repetition limits are not exceeded
- retry/script budget remains
- no protected-anchor, artifact-conflict, sentinel, or Codex brake blocks progress

Executor must escalate when:

- no scripted item receives a correct answer
- at least one answer is off-topic
- repeated failure exceeds policy
- protected anchors fail
- update/promotion is ready for decision
- grading confidence is too low
- queue or budget is exhausted

---

## Orchestrator Decision

When escalation occurs, the orchestrator decides:

- accept evidence and schedule next card
- update concept state and session archive
- replay same card with a repair script
- run eval or brain scan
- approve proposed training turns into a buffer
- apply micro-update
- reject unusable evidence
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
- no trainer script deviation
- target axis improved or intentionally stable
- protected anchors pass
- malformed/repetition rates below configured limits
- no high-severity new failure

Threshold values come from `training/pipeline/msm/state/orchestrator_config.json`; the required
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

The executor writes `proposed_training.jsonl`. The orchestrator creates
`training/pipeline/msm/buffers/BUFFER_ID/approved_training.jsonl` by selecting records from one
or more proposal files. A micro-update may run when the configured buffer policy is met
or when the orchestrator explicitly approves a single-session repair update.

---

## Scheduler State Rule

Report cards are immutable evidence, but scheduler decisions should read accumulated state:

- per-axis attempt count
- original and post-correction successes
- failures, off-topic answers, malformed answers
- last strategy and last session
- strategy-level children count

The default scoring shape is:

```text
learnability + severity + underexplored_bonus - retry_penalty
```

This is a policy input, not a promotion gate. Protected-anchor failures still block
promotion directly.

---

## Brain Scan Rule

Run a brain scan when chat reports show a stable confusion but do not explain the route:

- same-category identity confusion
- cross-category bleed
- protected anchor routed through fragile hubs
- repair works in one prompt form but fails nearby forms

Brain scans diagnose routing. They do not promote update candidates by themselves.
