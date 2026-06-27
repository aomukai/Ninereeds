# Iteration Schema

Campaign iterations are autonomous experiments. They do not need approval between
steps when they follow this schema.

## Roles

- `current_best`: checkpoint to protect. New branches start from this checkpoint.
- `candidate`: checkpoint produced by the current branch.
- `default_eval`: broad grounding gate from `meta/scripts/eval_grounding.py`.
- `target_eval`: focused test suite for the current failure mode.
- `manual_gate`: greedy probe transcript for human reading.

## Loop

1. Start from `current_best`.
2. Build a small repair or review corpus for the observed failure.
3. Train one epoch at low learning rate.
4. Run default eval, target eval, and manual gate.
5. Decide:
   - keep candidate if default eval is not worse and target eval improves
   - continue candidate if both default and target eval improve
   - roll back if default eval drops below gate
   - change dose if target improves but default drops
   - change examples if target does not improve
6. Record result in the campaign log and summary JSONL.
7. Repeat until the goal is met or the branch is clearly worse.

## Default Gates For C17

- protect `core/c17_contrast_angle_1200_e4.pt`
- promotion candidate should reach at least default `5/7`, avg `0.905`
- boundary target should reach at least avg `0.85`
- rollback branch if default drops below `4/7` or avg `0.85`

## Repair Dose Rules

- start with 300-700 examples
- use balanced positive + negative pairs
- avoid repair-only repetition unless proving a single boundary
- use `2e-5` for repair from a good checkpoint
- use contrast-review after repair, not sorted order

## Triplet Rule

Do not introduce triplets into the kernel until short-answer gates are stable.
Triplets are for prose fluency and richer concepts after category boundaries hold.

## Damaged-Concept Test

When a small set of concepts is damaged, train only that concept set for one
low-LR epoch as a diagnostic. Keep it only if the default eval does not regress.
