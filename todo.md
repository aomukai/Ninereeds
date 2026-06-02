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
- [ ] Build curriculum order: Phase A → Phase B → grounded_stories (195) → teaching_stories → B/D/E retry
- [ ] Boolean story pass: run `meta/scripts/story_gen_boolean.py` (to be written) on final living list — spec in `docs/boolean_stories.md`
- [ ] Write `docs/probe_catalogue.md` — competency probe design (skeleton drafted in session 2026-06-02)

---

## Campaign 14 — Grounded stories + Phase B retry

**Goal:** Introduce grounded stories on top of the C13 winner, then retry Phase B and D.
Hypothesis: narrative context gives emotions and cognitive verbs the grounding they need.

**Model:** 25M (validate) → 150M (if 25M confirms)
**Base checkpoint:** `checkpoints/c13_Phase_C_winner.pt` (shaped 0.925)

### Immediate next steps

- [ ] Train grounded stories (interleaved, ≤5% of corpus) on C13 winner
- [ ] Eval: does shaped score hold or improve?
- [ ] Retry Phase B (emotions/movement) from stories checkpoint
- [ ] Retry Phase D (cognitive verbs) from stories checkpoint
- [ ] If B or D absorb: retry Phase E (abstraction/math) — needs arithmetic_bridge first

---

## Standing work (lower urgency)

- [ ] Phase I — Corpus critic (`meta/scripts/corpus_critic.py`) — before any full-scale campaign
- [ ] Phase E — Wiki splitting (for finer curriculum ordering)
- [ ] Phase H — Ordering manifests (depends on Phase E)
- [ ] Fix `allowlist_rank` not propagating into JSONL units (cosmetic; doesn't affect training order)
