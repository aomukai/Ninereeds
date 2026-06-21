# Ninereeds — Session Index

Read this after `CLAUDE.md`. Together they are sufficient to start any session.

Last updated: 2026-06-22

---

## Session startup

1. `CLAUDE.md` — dispatch policy, hard constraints, platform rules, tool map
2. `index.md` — this file: current state, key pointers
3. `todo.md` — active work queue
4. Run Step 0 from `training/pipeline/runbook.md` — check for running training processes

---

## Current state

| Field | Value |
|---|---|
| Latest complete campaign | C15 — complete |
| Final C15 winner | `checkpoints/c15_vignettes_winner.pt` (arith_jp 0.937, shaped 0.987) — education winner is damaged |
| Active work | Corpus redesign — `training_data/redesign/` — concept anchoring from scratch |
| Next training | First epoch on redesign corpus; see `todo.md` |
| Key redesign decision | EN-first, concept anchoring, "I don't know" as first-class response, variable-length files |

*Update this table at the start of each new session.*

---

## Key references

| What | Where |
|---|---|
| Campaign procedure + eval philosophy | `training/pipeline/runbook.md` |
| Corpus redesign spec + curriculum tiers | `training_data/redesign.md` |
| DeepSeek generation brief | `training_data/redesign/deepseek_brief.md` |
| Pipeline automation design | `training/pipeline/pipeline.md` |
| Corpus inventory, campaign history | `training/pipeline/curriculum_topology.md` |
| Intervention registry, conventions | `training/pipeline/training.md` |
| Active work queue | `todo.md` |
| Completed work log | `history.md` |
| Brain map methodology | `docs/brain_map.md` |

---

## Project layout

```
training_data/          corpus — 5 folders (01_language → 05_philosophy)
training/
  corpus/               built .txt files — one per block, validated
  corpus_admin/         manifests, probe sets
  logs/campaign_N_reports/  per-campaign block reports + brain maps
  pipeline/             runbook.md, pipeline.md, training.md, curriculum_topology.md
checkpoints/            promoted winners — never delete
core/                   in-training weights — do not touch while training runs
docs/                   brain_map.md, grammar_plan.md (research notes)
meta/scripts/           all batch runners, generators, eval tools
```

---

## Platform

- Python: `/home/aomukai/.unsloth/studio/unsloth_studio/bin/python`
- Training GPU: `CUDA_VISIBLE_DEVICES=0` (always; GPU 1 is daily-use card)
- Model: `bdh.py` — 25M default; `--scale-150m` / `--scale-600m` for larger; **do not modify**
- Checkpoints: `core/*.pt` and `checkpoints/` are gitignored — local only
