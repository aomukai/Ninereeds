# Ninereeds / BDH Cognitive OS

![BDH Cognitive OS](BDH.png)

This repository has two closely related goals:

1. **build the model itself** — a Developmental Learner Model (DLM) we are giving the proper name **Ninereeds**
2. **build the future OS around that model** — the BDH Cognitive OS runtime, LoRA harness, artifact system, and offline learning workflow that will come after the model is ready for it

Right now, the center of gravity is the **active training loop**: the corpus is complete and Ninereeds is being trained and evaluated run by run, with per-epoch probes and shaped-score tracking driving each intervention decision.

The OS/harness side is still important, but it is **not the current priority**. The long-term plan is to give Ninereeds a modular runtime with explicit routing, artifact logging, LoRA-based specialization, and offline consolidation. The near-term job is to make sure there is a real model worth building that system around.

## What Kind of Model Is This

Ninereeds is a **Developmental Learner Model (DLM)** — not a large language model.

The distinction matters:
- "Large" does not apply — Ninereeds is ~25M parameters. There is no error averaging from scale. Every malformed training file has outsized impact.
- "Language" is not the defining point — the goal is not broad linguistic coverage but a coherent, well-grounded knowledge structure built through a staged curriculum. The learning behaviour more closely resembles a student working through a structured course than a model trained on web-scale text.
- "Developmental" is the key word — Ninereeds is trained in phases, with curriculum sequencing, paraphrase pressure, and retrieval-frame sensitivity that mirror second-language acquisition patterns in human learners. Understanding a concept and reliably producing it under retrieval pressure are treated as distinct stages.

The DLM framing shapes every design decision: curriculum ordering, drill sequencing, the 4-phase paraphrase arc, and why shaped score (shaper-routed inference) is the primary metric rather than raw perplexity.

---

## The Name

The model's proper name is **Ninereeds**.

The name comes from Terry Pratchett's *The Colour of Magic*: Ninereeds is the name of a dragon in the novel. That keeps the naming lineage intact with Pathway's **Baby Dragon** architecture while giving this project's model a proper individual name instead of calling the model by the architecture name.

## What We Are Building

### 1. The model

The intended model direction is:
- trained from scratch rather than treated as a thin wrapper around an existing assistant
- shaped through highly explicit curriculum design instead of broad noisy web-scale ingestion
- grounded in staged language learning: early curriculum → wiki knowledge → bridge material → story layers → later training infrastructure
- designed to become a boundary-aware, interest-forming, offline-capable core rather than a permanently internet-dependent chatbot

### 2. The training data

A large part of this repo is the construction of the training corpus itself.

That work currently includes:
- **Phase 1–5 rewritten curriculum** in `training_data/phases/`
- **wiki corpus** in `training_data/wiki/`
- **Phase 6 bridge** material in `training_data/phases/phase_6/`
- **story-layer planning and batches** in `training_data/triplet_stories/`

This data work is not secondary bookkeeping. It is part of the model-building process itself.

### 3. The future OS / harness

The repo also contains the planned and partially scaffolded path toward **BDH Cognitive OS**:
- a runtime around the model
- explicit session snapshots and disk artifacts
- future LoRA selection / routing
- specialist vs clean-core phases
- offline dream / consolidation workflows
- reproducible evaluation and verifier-style loops

That system matters, but it comes **after** the model is sufficiently real to justify it.

## Current Project State

At the moment, the repository is best understood as:
- **active training loop** — corpus complete, multiple runs evaluated, run 6 in progress
- **early runtime / harness scaffolding for later stages**

Concretely:
- `bdh.py` and `core/` preserve the upstream BDH architecture/checkpoint artifacts; `core/` also receives epoch checkpoints during active training runs
- `checkpoints/` holds the promoted best-of-run checkpoints (the lineage that matters)
- `training_data/` is the completed corpus — no longer the primary area of active change
- `training/logs/` is now the most actively evolving part of the repo: per-epoch probe results, eval scores, run reports
- `docs/training.md` is the current authority — it contains the training harness design, intervention registry, and step-by-step manual
- `todo.md` tracks the active training queue and checkpoint lineage
- runtime files like `harness.py`, `inference.py`, `prompt_shaper.py`, and `eval.py` represent the OS-side direction, but the repo should not be read as "mainly a harness project"

## Repository Map

```text
AGENTS.md                  implementation contract for coding agents
README.md                  repository overview
todo.md                    active training queue and checkpoint lineage
docs/training.md           training authority: harness design + step-by-step manual
archive/                   archived legacy queues/status docs
bdh.py                     upstream BDH architecture reference (read-only)
core/                      upstream checkpoint assets + active epoch checkpoints
checkpoints/               promoted best-of-run checkpoints (the lineage)
docs/                      design and planning documents
inventory/                 allowlist.txt and word/concept lists
meta/scripts/              batch runners, generators, verifiers
training_data/             completed corpus: phases, wiki, lang, stories, reasoning
training/logs/             run reports and training logs (primary active area)
harness.py                 early runtime entry point / scaffold
inference.py               BDH loading and generation wrapper
prompt_shaper.py           prompt shaping layer
eval.py                    prompt-shaping evaluation harness
train.py                   training entry point
loras/                     future skill/dream adapter area
```

## The Corpus (complete)

The training corpus lives under `training_data/`. The foundational corpus is complete; current additions focus on targeted grounding, reasoning drills, and intervention-driven refinement. It is not the primary area of active work, but understanding it helps understand what Ninereeds has been trained on.

### Foundation curriculum — `training_data/phases/`

Six phases of tightly controlled `[user]`/`[Ninereeds]` dialogue files: concrete nouns, abstract adjectives, gerunds, bridge words, and more. Dependency-ordered so each concept builds on previously introduced vocabulary.

### Language curriculum — `training_data/lang/`

Five levels covering multilingual word files (EN/DE/JP/ZH), semantic frames, dative/genitive constructions, spatial structures, and Q&A pairs. All five levels complete.

### Knowledge layer — `training_data/wiki/`

Grouped concept knowledge in question-answer style. Levels 1–4.

### Story layers — `training_data/triplet_stories/`

1345 narrative stories per language (EN/DE/JP/ZH) across four tiers. Teach how things act and relate in context. Interleaved with the phase corpus during training.

### Reasoning — `training_data/reasoning/`

27 EN reasoning and arithmetic files × 4 languages (EN/DE/JP/ZH). Currently subject to active experimentation via `oversample_cluster` intervention (see `docs/training.md`).

## OS / Harness Direction

The long-term system design lives in:
- `docs/bdh_cognitive_os_design.md`

That design describes a future runtime with:
- core model + selected specialist path
- artifact-first execution
- clean-core reintegration
- future LoRA routing / registry
- offline dream-style consolidation

Important clarification: this design is the **target architecture**, not the best one-line summary of the repo's present focus.

A better present-tense summary is:

> We are building Ninereeds first, and building BDH Cognitive OS around Ninereeds second.

## Core Rules

- Never modify `bdh.py`
- Never modify anything in `core/`
- Never train during the live inference loop
- Never silently mutate model weights during a run
- Always write important outputs to disk
- Keep specialist and clean-core phases separate once the OS-side runtime is active

The fuller agent-facing contract is in [AGENTS.md](AGENTS.md).

## Useful Entry Points

If you are trying to understand the repo quickly, start here:

1. `README.md` — this file
2. `docs/training.md` — training authority: harness design, intervention registry, manual
3. `todo.md` — active run queue and checkpoint lineage
4. `training/logs/run_6_report.md` — most recent run (in progress)
5. `AGENTS.md` — implementation contract for coding agents
6. `docs/bdh_cognitive_os_design.md` — long-term OS/harness direction

## Active Training Scripts

These are the primary tools in the current training loop:

| Script | Role |
|---|---|
| `train.py` | Training entry point — runs epochs, saves per-epoch checkpoints |
| `eval.py` | Shaped-score evaluation — primary metric for checkpoint selection |
| `meta/scripts/probe.py` | 12-probe format diagnostic — run after every epoch |
| `inference.py` | BDH loading and generation wrapper |
| `prompt_shaper.py` | Prompt routing layer — drives the shaped score |

The full procedure is in `docs/training.md`. The active run and checkpoint lineage are in `todo.md`.

## Attribution

The upstream **BDH** architecture and the core implementation in `bdh.py` come from Pathway Technology, Inc.

- Paper: <https://arxiv.org/abs/2509.26507>
- Repository: <https://github.com/pathwaycom/bdh>

This repository builds a broader project around that base: curriculum creation, active training runs with per-epoch evaluation, and the eventual OS/harness intended to support Ninereeds.

**Ninereeds is a name inspired by Terry Pratchett’s Discworld. This project is not affiliated with or endorsed by the Pratchett estate.**

## License

- Upstream BDH core: original upstream repository license
- Surrounding project files in this repo: MIT License unless noted otherwise

© Andi Omukai
