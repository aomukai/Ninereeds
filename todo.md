# TODO

Active work queue. See `training/docs/training.md` for the full procedure.
Completed phases: `archive/milestones/2026-05-29_corpus_milestone.md`.

---

## Nomenclature

**Campaign** = one experimental run covering one or more training phases.
A campaign ends when all planned phases complete or a regression warrants stopping.
Reports live in `training/logs/campaign_N_reports/`, named `NN_phase_X.md`.

---

## Campaign 13 — COMPLETE

**Result:** Bridge → Phase A → Phase C = shaped **0.925** (25M)
**Final checkpoint:** `checkpoints/c13_Phase_C_winner.pt`
**Report:** `training/logs/campaign_13_reports/orchestrator_log.md`

### Findings

- Bridge as cold-start primer: **+0.007** (Fresh → Bridge → Phase A beat Phase A-only)
- Bridge as between-phase connector: **-0.008 to -0.018** (consistently hurt — do not use)
- Phase C (agents & social) absorbed cleanly after Phase A (+0.004)
- Phase B (emotions/movement), D (cognitive verbs/time), E (abstraction/math): all permanently failed after 4 attempts each
- Extension pass confirmed: 0.925 is the ceiling for this curriculum on 25M

### Why B/D/E failed

Phase B contains 400+ emotion and desire-verb units — relational and temporal, incompatible
with the static-property phase format without narrative grounding.
Phase D (think/know/time/truth) and Phase E (abstraction/math) have the same problem at greater depth.

---

## Teaching stories — REDESIGN (2026-06-01)

**Goal:** New corpus layer to ground B/D/E concepts through narrative before retry.
**Base:** C13 Phase C winner (0.925). Teaching stories replace old Phase B/D/E format.

### New phase nomenclature

| Phase | Content | Status |
|---|---|---|
| A | Concrete anchors | Done (C13) |
| B | Agents & social (was C) | Done (C13) |
| C–F | Teaching stories (4 complexity tiers) | Pipeline redesign in progress |

### Corpus state (2026-06-01)

- `training_data/phase_A/` — active (1494 units in phase_A_order.jsonl)
- `training_data/phase_B/` — active (1148 units, was phase_C — agents/social)
- `training_data/teaching_stories/` — empty, ready for new generation
- `archive/phases/phase_B_old/` — old emotions/movement (B/D/E failed C13)
- `archive/phases/phase_D_old/`, `phase_E_old/` — archived
- `tmp/phase_vocab.jsonl` — 2545 tier-1 (B/D/E) schemas intact, 2608 tier-2 (A/C) records

### Living list design

- **Tier 1 (never shown):** B/D/E concepts — need anchor story first
- **Tier 2 (anchor written):** moves here after anchor story generated
- **Tier 3 (covered):** after ≥5 non-anchor appearances
- A/C concepts start at tier 2 (were anchors in old phases)
- `n_times_used` field tracks non-anchor appearances
- Story complexity cycles 1→2→3→4→1, floored at concept's `entry_tier`
- Word priority weighted by `wordfreq` Zipf score

### Next steps

- [x] Generator written + hardened (`meta/scripts/story_gen_v2.py`)
- [x] Prompt corrected: omniscient narrator, NO named characters (Emma/Taro/Gran/Biscuit/Bello removed — those belong to grounded_stories only)
- [x] 845 test stories cleared; vocab/tracker/state reset to zero
- [x] Handoff doc: `docs/handoff_2026-06-02.md` — read this before starting on Windows

**NEXT ACTION (Linux):** resume generation run (stopped cleanly at 1699 stories):
```
python3 meta/scripts/story_gen_v2.py run --workers 4 2>&1 | tee -a tmp/story_gen_run.log
```
State on stop: anchor pass in progress, 1699/~2545+ stories done, 846 tier-1 words still need anchor.
See `docs/handoff_2026-06-01.md` for full details.

- [x] Full generation run complete (5006 stories, 2026-06-02)
- [x] Audit passes clean
- [x] Commit teaching_stories/ to git
- [x] Boolean story pass: 800 stories complete (2026-06-02), committed
- [x] Build curriculum order: phase_A → phase_B → lang_1/2 → bridge → grammar → lang_3/4/5 → teaching+triplets → boolean
  - `training/corpus_admin/campaign14_manifest.txt` — 37,569 files, complete explicit order (2026-06-04)
  - `training/corpus_admin/campaign14_blocks/` — 8 individual block files for verification
  - `meta/scripts/build_campaign14_manifest.py` — manifest generator (`--verify` flag checks all paths)
  - (old `campaign14_order.txt` superseded — teaching block only, had grounded interleaved — keep for reference)
- [x] Write `docs/probe_catalogue.md` — complete (2026-06-02); language probe set built (2026-06-04)
  - `training/corpus_admin/probe_sets/language.jsonl` — 104 probes, 16 categories
  - `meta/scripts/brain_map.py` — fixed paths; added `--probes` and `--name` flags

---

## Campaign 14 — Language campaign

**Goal:** Teach the full language curriculum. Retry B/D/E after language is established.
**Design:** 4-campaign split: 01_language → 02_thinking → 03_education → 04_philosophy

**Model:** 25M (validate) → 150M (if 25M confirms)
**Base checkpoint:** `checkpoints/c13_Phase_C_winner.pt` (shaped 0.925)
**Training data:** `training_data/01_language/` (restructured 2026-06-04)

### Immediate next steps

- [ ] Build training corpus: `python3 meta/scripts/build_training_corpus.py --order-file training/corpus_admin/campaign14_manifest.txt --output training/corpus/campaign14_full.txt`
- [ ] Verify corpus: output must end with `All files validated — corpus is clean.`
- [ ] Update `CLAUDE.md` corpus structure section to reflect new `01_language/` paths
- [ ] Update `docs/probe_catalogue.md` diagnostic grep commands (still reference old paths)
- [ ] Launch Campaign 14 training (see `training/docs/training.md` Step 6)
- [ ] After each epoch: run probe + eval + brain_map (language probe set)

---

## Campaign 15 — Thinking campaign (02_thinking)

**Goal:** World model + reasoning on top of language-trained checkpoint.
**Data:** `training_data/02_thinking/` — grounded_stories (sequential), reasoning

### Next steps (after Campaign 14 completes)
- [ ] Build `meta/scripts/build_campaign15_manifest.py` (same pattern as C14)
  - grounded_stories: sequential, do NOT domain-sort
  - reasoning: natural file order
- [ ] Build `training/corpus_admin/probe_sets/thinking.jsonl`

---

## Campaign 15 design — three key experiments (2026-06-02, details TBD)

From deep-research report (2026-06-02). Run in order; each informs the next.

### Experiment 1: Atlas reproducibility + cluster drift
**Question:** Are the brain map clusters stable across seeds and checkpoints, or seed-specific noise?
**Method:** Run `meta/scripts/brain_map.py` on C13 Phase A winner checkpoint + at least 2 seeds of C13 Phase C winner. Compare cluster signatures (centroid, co-firing overlap, probe coverage) — NOT raw neuron IDs.
**Why first:** Cluster-based interventions (lesions, specialist transfer) are only trustworthy if clusters are stable. This is a prerequisite for everything else.
- [ ] Define cluster signature matching method
- [ ] Run brain map on `checkpoints/c13_phaseA_winner.pt`
- [ ] Compare Phase A vs Phase C winner cluster structure

### Experiment 2: Teaching stories + triplets interleaving matrix
**Question:** Does alternating teaching stories and triplets (aligned by category) improve B/D/E absorption vs sequential?
**Conditions:** sequential (teaching then triplets) vs aligned interleave (by domain) vs random interleave
**Controls:** matched token budgets; same base checkpoint
**Why second:** Directly tests the B/D/E bottleneck and the register-alignment hypothesis together.
- [ ] Design interleave schedules
- [ ] Build corpus builder support for interleaving
- [ ] 25M pilot on best 2 schedules

### Experiment 3: Register-alignment crossover
**Question:** Does the same concept activate different circuits in Q&A format vs story format? Does cross-register transfer happen?
**Method:** Add triplet-format probes to brain_map.py ("tell me a story about X" for same concepts as Q&A probes). Compare activation clusters. Then test: does training in one register transfer to the other?
**Why third:** If Q&A and story formats activate different circuits for the same concept, interleaving is not just varied exposure — it teaches multi-register access. If they converge, format doesn't matter.
- [ ] Add triplet-format probes to `meta/scripts/brain_map.py`
- [ ] Run crossover brain map on C13 winner
- [ ] Design training experiment if activation clusters diverge

---

## Standing work (lower urgency)

- [ ] Phase I — Corpus critic (`meta/scripts/corpus_critic.py`) — before any full-scale campaign
- [ ] Phase E — Wiki splitting (for finer curriculum ordering)
- [ ] Phase H — Ordering manifests (depends on Phase E)
- [ ] Fix `allowlist_rank` not propagating into JSONL units (cosmetic; doesn't affect training order)
