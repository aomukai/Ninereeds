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

## Corpus — campaign structure

Training data is split into four numbered campaign folders. Training order: 01 → 02 → 03 → 04.

### 01_language/

| Subcorpus | Path | Notes |
|---|---|---|
| Phase A (concrete anchors) | `training_data/01_language/phase_A/` | 1494 units. Foundation vocabulary. |
| Phase B (agents & social) | `training_data/01_language/phase_B/` | 1148 units. Was Phase C in C13. |
| Teaching stories | `training_data/01_language/teaching_stories/tier_N/bucket/` | 5006 stories, 4 tiers × 50 domain buckets. |
| Boolean stories | `training_data/01_language/boolean_stories/` | 800 files. Elimination/contrast register. Comes after teaching block. |
| Triplet stories | `training_data/01_language/triplet_stories/tier_1/`–`tier_4/` | 1345 EN × 4 langs. Aligned by domain with teaching stories. |
| Lang curriculum (1–5) | `training_data/01_language/lang/` | ~12k files. Multilingual 4-stanza format. lang_1/2 early; lang_3/4/5 after grammar. |
| Grammar curriculum | `training_data/01_language/grammar/` | 1400 files, 11 modules. Numeric dir order = training order. Dative/accusative spine. |
| Bridge course | `training_data/01_language/bridge/` | 234 files. 001-100: DAT double-object; 101-234: 4-case permutations. Precedes grammar. |
| Grammar design rationale | `docs/grammar_plan.md` | Why function-first. Still relevant as WHY doc. |
| Grammar control files | `training/corpus_admin/grammar/` | manifest.md, lexicon.md, prepositions.md. Not training data. |

### 02_thinking/

| Subcorpus | Path | Notes |
|---|---|---|
| Grounded stories | `training_data/02_thinking/grounded_stories/` | 195 stories × 4 langs = 780 files. Sequential world model — do not shuffle. |
| World bible + storylist | `training/corpus_admin/grounded_stories/` | Generation spec. Not training data. |
| Reasoning | `training_data/02_thinking/reasoning/` | 153 files. Maths, epistemic uncertainty, counting. |

### 03_social_cognitive/

| Subcorpus | Path | Notes |
|---|---|---|
| Wiki (levels 1–4) | `training_data/03_social_cognitive/wiki/level_N/` | ~8400 files. Long-form encyclopedic Q&A. |

### 04_philosophy/

| Subcorpus | Path | Notes |
|---|---|---|
| Philosophy dialogues | `training_data/04_philosophy/` | 144 files (flat). Socratic dialogues in 4 languages. Epistemic humility / limits of knowledge. Capstone campaign. |

### CKS curriculum pipeline (04_education/ — not a training campaign)

| File | Path | Notes |
|---|---|---|
| Preschool concept nodes | `training_data/04_education/phase1_preschool.jsonl` | 34 entries. Phase 1 ontology from CKS preschool PDF. |
| K-8 concept nodes | `training_data/04_education/phase1_k8.jsonl` | 164 entries (KG–G8). Phase 1 ontology from CKS K-8 PDF. |
| Curriculum design | `training_data/ninereeds_cks_curriculum.md` | 5-phase pipeline spec. |

Pipeline: Phase 1 JSONL → Phase 2 (DeepSeek adds `facts`) → Phase 2.5 (Claude audit) → Phase 3 (linking pass) → Phase 4 (DeepSeek generates dialogue `.md` files).

### Cross-corpus

| Topic | Where |
|---|---|
| Allowlist | `inventory/allowlist.txt` | Content word gate for all corpus generation. |
| Phase vocab / domain labels | `tmp/phase_vocab.jsonl` | 2545 tier-1 + 2608 tier-2 word schemas with domain tags. |
| Campaign 14 order manifest | `training/corpus_admin/campaign14_order.txt` | 10,034-file interleaved order (teaching + boolean + triplets). |
| Teaching story manifest | `training/corpus_admin/teaching_story_manifest.md` | 5806 entries, domain-sorted, 8 blocks. |

---

## Corpus generation scripts

Active scripts used in the current training cycle:

| Script | Purpose | Key usage |
|---|---|---|
| `meta/scripts/build_training_corpus.py` | Assemble corpus text file from an order manifest | `--order-file training/corpus_admin/campaign14_order.txt --output ...` |
| `meta/scripts/build_teaching_order.py` | Generate campaign14_order.txt (teaching+boolean+triplets+grounded interleaved) | `stats` / `manifest` / `interleave [--dry-run]` |
| `meta/scripts/story_gen_v2.py` | Teaching story generator (tier+domain aware, anchor/organic passes) | `run --workers 4` |
| `meta/scripts/story_gen_boolean.py` | Boolean story generator (plan/run/status) | `plan --target 200`, `run --workers 4` |
| `meta/scripts/brain_map.py` | Activation atlas scanner — see Eval section | `probe`, `hubs`, `map` |
| `meta/scripts/probe.py` | Qualitative output probes (12 categories) | `--checkpoint $CKPT --temperature 0.7 --tokens 120` |

Legacy generation scripts (generation complete; kept for reference):

| Script | What it generated |
|---|---|
| `meta/scripts/gen_stories.py` | Grounded stories (EN/DE/JP/ZH) |
| `meta/scripts/localize_wiki.py` | Wiki DE/JP/ZH |
| `meta/scripts/lang_gen.py` | lang_1 files |
| `meta/scripts/lang4.py`, `lang4d.py` | lang_4 structural + story corpus |
| `meta/scripts/lang5.py`, `lang5d.py` | lang_5 Q&A + story corpus |
| `meta/scripts/lang3c.py`, `lang3d.py` | lang_3 reflexive/benefactive + parallel stories |
| `meta/scripts/localize_triplets.py` | Triplet story DE/JP/ZH localizations |
| `meta/scripts/localize_reasoning.py` | Reasoning DE/JP/ZH |
| `meta/scripts/localize_philosophy.py` | Philosophy multilingual expansion |
| `meta/scripts/repair_formatting_opencode.py` | Phase formatting repairs (queue done) |
| `meta/scripts/gen_grammar.py` | Grammar corpus (complete) |

---

## Eval and probing

Three tools, run in this order after every epoch checkpoint:

| Tool | Purpose | Usage |
|---|---|---|
| `meta/scripts/probe.py` | Qualitative output quality — 12 categories (phase format, lang curriculum, narrative+reasoning) | `python meta/scripts/probe.py --checkpoint $CKPT --temperature 0.7 --tokens 120` |
| `eval.py` | Quantitative shaped and raw scores across 18 prompts | `python eval.py --checkpoint $CKPT` |
| `meta/scripts/brain_map.py` | Activation-geometry scan — records xy_sparse co-firing at last prompt token, all layers | `python meta/scripts/brain_map.py probe --checkpoint $CKPT [--name label]` |

### Brain map

`brain_map.py` takes an MRI of the model's weight activations. It records which neuron clusters
co-fire for a given probe, producing a PCA scatter and cosine similarity heatmap.
Use it to track whether training moved the right clusters, created new ones, or caused bleed.

**Usage:**
```bash
# Run a full scan with the language probe set, name the outputs
python3 meta/scripts/brain_map.py probe \
  --checkpoint checkpoints/c14_e2.pt \
  --probes training/corpus_admin/probe_sets/language.jsonl \
  --name c14_e2_language

# Generate visuals from saved activations (no checkpoint needed)
python3 meta/scripts/brain_map.py map --name c14_e2_language

# Hub analysis
python3 meta/scripts/brain_map.py hubs --name c14_e2_language --threshold 0.7
```

**Output files** (namespaced by `--name` so multiple scans coexist):

| File | Contents |
|---|---|
| `tmp/brain_map_<name>_activations.npz` | Raw xy_sparse vectors per probe (reusable) |
| `tmp/brain_map_<name>_probes.jsonl` | Probe metadata + sparsity per probe |
| `tmp/brain_map_<name>_similarity.png` | Cosine similarity heatmap |
| `tmp/brain_map_<name>_scatter.png` | t-SNE / PCA scatter |
| `tmp/brain_map_hubs.json` | Hub analysis output |

**v1 status:** activation-geometry diagnostic — detects prompt-family differences reliably.
Not yet a semantic map (template controls pending). See `docs/brain_map.md` for correct interpretation
of v1 findings and the v2 requirements (template crossover, negative controls, construction-split grammar probes).

### Probe sets (scanner databases)

The scanner and the probe definitions are separated. Probe sets live in:
```
training/corpus_admin/probe_sets/
  language.jsonl    — 104 probes for Campaign 14 (language campaign)
  thinking.jsonl    — (future: Campaign 15)
  education.jsonl   — (future: Campaign 16)
  philosophy.jsonl  — (future: Campaign 17)
```

Each probe record: `{"id", "campaign", "category", "lang", "prompt", "expected_cluster"}`
The `prompt` field is the fully-formatted `[user]...\n[Ninereeds]` string the model receives.

**Human-readable design doc:** `docs/probe_catalogue.md` — 9 cluster groups with PASS/WARN/FAIL
criteria and C14 target cluster signatures. The `.jsonl` files are the machine-readable implementation.

### Shaped score

Shaped score is the primary metric — raw improvement without shaped improvement is not success.
Definition and failure modes: `training/docs/training.md` (Shaped score section).
Prompt shaper: `prompt_shaper.py` (root).
Per-run results: `training/logs/run_N_report.md` or `training/logs/campaign_N_reports/`.

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
| Activation atlas (brain map) — full plan | `docs/brain_map.md` | Phase 1 complete (C13 scan); Phase 1b (template crossover, negative controls) in design |
| Curriculum ordering research | `docs/curriculum_topology.md` | Active reference — bridge interpretation corrected 2026-06-02 |
| Convergence training (mommy says) | `training/docs/mommy_says_machine.md` | Available as L1-I in intervention registry; first candidate: German dative |
| Sparse modular training / specialist composition | `docs/brain_map.md` (Phase 5) | 🔮 Requires stable cluster validation first |
| BDH cognitive OS design | `docs/bdh_cognitive_os_design.md` | Long-term architecture vision |
| BDH long-term vision | `docs/bdh_long_term_vision.md` | Long-term vision |
| Hebbian implications | `docs/hebbian_implications_for_bdh.md` | Theory / research |

---

## Project history

| Topic | Where |
|---|---|
| What was tried and why | `docs/project_history.md` |
| Completed tasks log | `docs/history.md` |
| Phase milestones detail | `archive/milestones/2026-05-29_corpus_milestone.md` |
| Recent session handoffs | `docs/handoff_YYYY-MM-DD*.md` — one per session; grep for the date range you need |
| Git log | `git log --oneline` |

The handoff docs + git log together form the best recent history: handoffs record decisions and rationale, commits record what changed on disk.

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
