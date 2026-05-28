# Ninereeds — Knowledge Map

Where to find information about any part of the project.
Read this when you're not sure where something lives.

⚠️ = known to be stale or partially outdated  
🔮 = planned / not yet implemented

---

## Start here (every session)

| What | Where |
|---|---|
| Session startup procedure | `CLAUDE.md` or `CODEX.md` respectively |
| Active work queue | `todo.md` |
| Training step-by-step | `training/docs/training.md` |
| Completed phases (history) | `archive/milestones/2026-05-29_corpus_milestone.md` |

---

## Training

| Topic | Where | Notes |
|---|---|---|
| Full training procedure | `training/docs/training.md` | Authoritative. Step 0, probe, eval, promote. |
| Corpus layer descriptions | `training/docs/pipeline.md` | Stage-by-stage curriculum plan. Updated 2026-05-29. |
| Run history (1–12) | `memory/project_training_runs.md` | Epoch sweet spots, corpora, key findings per run. |
| Training harness | `training/harness/` | `train.py` lives at root; harness support files here. |
| Run logs and reports | `training/logs/` | One `run_N_report.md` per run. |
| Corpus build outputs | `training/corpus/` | `full_corpus.txt`, per-run corpus snapshots. |
| Sequential mode | `train.py --sequential` | Implemented 2026-05-24. Smoke-tested. Needed for run 13. |

---

## Corpus

| Topic | Where | Notes |
|---|---|---|
| Corpus structure overview | `CLAUDE.md` (Corpus structure section) | File tree, naming conventions, format rules. |
| Phase files (1–6) | `training_data/phases/` | EN + DE/JP/ZH. 5806 × 4 = 23,224 files. |
| Lang curriculum (1–5) | `training_data/lang/` | ~18k files. Flat dirs, prefix = sublevel. |
| Wiki (levels 1–4) | `training_data/wiki/` | 2110 EN × 4 langs = 8440 files. |
| Grammar corpus | `training_data/grammar/` | 1921 files. Numeric dir order = training order. |
| Grammar design rationale | `docs/grammar_plan.md` | Why function-first. Dative/accusative spine. Still relevant as WHY doc even though generation is complete. |
| Grammar control files | `training/corpus_admin/grammar/` | manifest.md, lexicon.md, prepositions.md, bridge_design.md. Not training data. |
| Grounded stories | `training_data/grounded_stories/` | 195 stories × 4 langs = 780 files. |
| World bible + storylist | `training/corpus_admin/grounded_stories/` | Generation spec. Not training data. |
| Triplet stories | `training_data/triplet_stories/tier_1/` – `tier_4/` | 1345 EN × 4 langs. |
| Reasoning | `training_data/reasoning/` | Maths, epistemic uncertainty, counting. |
| Philosophy | `training_data/philosophy/` | Multilingual tags: `[STATEMENT_EN/DE/JA/ZH]`. |
| Allowlist | `inventory/allowlist.txt` | Content word gate for stories and multilingual reference. |

---

## Corpus generation scripts

| Script | What it generates | Key flags |
|---|---|---|
| `meta/scripts/gen_stories.py` | Grounded stories (EN/DE/JP/ZH) | `gen --lang EN,DE,JP,ZH --workers 6` |
| `meta/scripts/localize_wiki.py` | Wiki DE/JP/ZH | `gen --level all --workers 8 --batch 10` |
| `meta/scripts/localize_phases.py` | Phase DE/JP/ZH | (run complete) |
| `meta/scripts/repair_formatting_opencode.py` | Phase formatting repairs | Queue: `phases/repair_formatting.txt` |
| `meta/scripts/fix_localizations.py` | Naturalness repairs from audit log | `--local` for LM Studio, `--model` to override |
| `meta/scripts/audit_localizations.py` | Naturalness audit → JSONL | `run --corpus phases --lang JP` |
| `meta/scripts/fix_grammar_punctuation.py` | CJK terminal punctuation | `--fix` |
| `meta/scripts/build_training_corpus.py` | Full corpus text file | Reads all training_data/ in order |

---

## Eval and probing

| Topic | Where |
|---|---|
| Eval harness | `eval.py` (root) |
| Probe script | `meta/scripts/probe.py` |
| Prompt shaper | `prompt_shaper.py` (root) |
| Shaped score definition | `training/docs/training.md` (Shaped score section) |
| Probe questions per run | `training/logs/run_N_report.md` |

---

## Architecture and model

| Topic | Where |
|---|---|
| Model definition | `bdh.py` (root) — **do not modify** |
| Core weights | `core/` — **do not modify** |
| Scale options | `training/docs/training.md` (Scale section) |
| LoRA adapters | `loras/` |
| Memory / activation study | `memory/project_scaling_study.md` |

---

## Long-term / research / future

| Topic | Where | Status |
|---|---|---|
| Activation atlas (brain map) | `docs/brain_map.md` | 🔮 Post-foundation-model run |
| Curriculum ordering research | `docs/curriculum_topology.md` | 🔮 Research brief for GPT/Gemini deep research |
| Convergence training (mommy says) | `training/docs/mommy_says_chatlog.md`, `training/docs/mommy_says_machine.md` | 🔮 Requires trained checkpoint |
| Sparse modular training | `memory/project_sparse_modular_training.md` | 🔮 Purpose-train → extract → compose |
| BDH cognitive OS design | `docs/bdh_cognitive_os_design.md` | Long-term architecture vision |
| BDH long-term vision | `docs/bdh_long_term_vision.md` | Long-term vision |
| Hebbian implications | `docs/hebbian_implications_for_bdh.md` | Theory / research |
| Grounded stories 196+ | `memory/project_grounded_stories_future.md` | Object permanence, ripple-uncertainty |

---

## Project history

| Topic | Where |
|---|---|
| What was tried and why | `docs/project_history.md` |
| Completed tasks log | `docs/history.md` |
| Phase milestones detail | `archive/milestones/2026-05-29_corpus_milestone.md` |
| Git log | `git log --oneline` |

---

## Agent role files

Each AI agent in the team has its own session guide. They used to be one `agents.md`
but are split by role because the agents are not equal.

| Agent | File | Purpose |
|---|---|---|
| Claude | `CLAUDE.md` | Session startup, dispatch policy, tool map, hard constraints when Claude is the orchestrator |
| Codex | `CODEX.md` | Session startup, dispatch policy, tool map, hard constraints when Codex is the Orchestrator |
| DeepSeek | `DEEPSEEK.md` | Worker role: bulk corpus generation, what DeepSeek does and does not decide |

---

## Known gaps

- `train.py`, `eval.py`, `harness.py` live at root alongside `bdh.py`. Could eventually move
  into `training/` but not worth the disruption until after run 13.
- Wiki (levels 1–4) is localised but not yet split into single-concept files (Phase E).
  Fine for training; needed for fine-grained curriculum ordering.
