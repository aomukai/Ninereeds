---
name: Ninereeds hard constraints — never violate
description: Files and behaviors that are permanently off-limits
type: feedback
originSessionId: f214e64f-85e7-459c-96c1-d360ca2cd70b
---
- bdh.py — never modify, never treat as anything other than reference
- core/ — never modify, read-only ground truth
- todo.md — only move items to history.md after file-level evidence the task is done
- No training during inference
- No silent weight mutation
- No auto-creating LoRAs
- No training until training_activation_audit.md is in a GO state

**Why:** These protect the model's integrity and the corpus's canonical state. Violations are silent and irreversible.

**How to apply:** Before any write or delete action, check whether the target is in the above list. If training_activation_audit.md is not GO, do not initiate any training run.
