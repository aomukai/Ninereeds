# Ninereeds — Session Index

Read this after `CLAUDE.md`. Together they are sufficient to start any session.

Last updated: 2026-06-28

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
| Latest complete campaign | C17 — kernel corpus and chat-capable core exploration |
| Protected C17 checkpoint | `core/c17_contrast_angle_1200_e4.pt` |
| Best C17 signal | Contrast-angle 1,200-concept run: default eval 5/7, avg 0.905 |
| Active campaign | None — C17 is closed |
| Active work | Design the concept-card tutor loop / Mommy Says machine |
| Next training | Wait for a designed tutor-loop scheduler or a deliberately scoped C18 experiment |
| Key C17 decision | Contrast ordering helped; broad/repair files were unstable; move from global corpus repair to per-concept adaptive lessons |

*Update this table at the start of each new session.*

---

## Key references

| What | Where |
|---|---|
| Campaign procedure + eval philosophy | `training/pipeline/runbook.md` |
| Brain map (3D graph) | `probe` → `hubs` → `graph`; open `training/logs/brain_maps/<name>_graph.html` |
| Brain trace (next-move report) | Generate `redesign_current.jsonl` → `validate-probes` → `trace`; read `training/logs/brain_maps/<name>_trace_report.md` |
| Kernel campaign spec | `kernel.md` |
| Identity corpus spec | `identity.md` |
| Kernel file format and commands | `training/corpus_admin/kernel/FORMAT.md` |
| C17 handoff | `training/logs/campaign_17_reports/01_handoff.md` |
| Tutor loop design | `training/pipeline/tutor_loop.md` |
| Mommy Says machine design | `training/pipeline/mommy_says_machine.md` |
| Corpus redesign spec + curriculum tiers | `training_data/redesign.md` |
| Pipeline automation design | `training/pipeline/pipeline.md` |
| Corpus inventory, campaign history | `training/pipeline/curriculum_topology.md` |
| Intervention registry, conventions | `training/pipeline/training.md` |
| Active work queue | `todo.md` |
| Completed work log | `history.md` |
| Brain map methodology | `docs/brain_map.md` |
| Brain trace manual | `docs/brain_trace_manual.md` |
| Current redesign probe generator | `meta/scripts/build_redesign_probe_set.py` → `training/corpus_admin/probe_sets/redesign_current.jsonl` |

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
