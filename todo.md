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

**Goal:** Teach language + thinking in one merged campaign before education and philosophy.
**Design:** 3-campaign split: C14 (01_language + 02_thinking) → C15 (03_education) → C16 (04_philosophy)
**Training uses block training** — separate `train.py` calls per block, each with its own LR arc + fresh Adam state.

**Model:** 25M (validate) → 150M (if 25M confirms)
**Base checkpoint:** `checkpoints/c13_Phase_C_winner.pt` (shaped 0.925)
**Training data:** `training_data/01_language/` + `training_data/02_thinking/`

**Block order (all --no-shuffle):**
1. `c14_01_language_core.txt` — full 01_language block (37,569 files)
2. `c14_02_arithmetic_bridge.txt` — c01–c15 Peano-ordered drills (15 files)
3. `c14_03_grounded_stories.txt` — grounded_stories sequential (780 files)
4. `c14_04_reasoning.txt` — reasoning/ (68 files; arithmetic concepts must land before this)

### Weekend runs (2026-06-06/07) — COMPLETE

- [x] Build training corpus: `training/corpus/campaign14_full.txt` — 37,569 files, 36 MB, clean
- [x] Variant A (bridge before grammar): 3 epochs complete — reports in `01_full_curriculum.md`
- [x] Variant B (bridge after grammar): launched, scanning each epoch automatically
- [x] Brain_map after every epoch — module status tracker updated in reports

**Key findings from A (E1→E3):**
- Vehicles (0.937→0.879) and objects (0.873→0.856): **DONE ×3** — drop from next run
- Grammar (0.284→0.201): persistently declining despite 531 dedicated neurons — needs bridge work
- Arithmetic: 1,296 dedicated neurons at E3, no cluster — needs direct-format drill files
- Multilingual (0.216→0.204): flat, not converging — needs more passes
- Model still growing; semantic neurons rising sharply (2316→3825 E1→E3) — not at ceiling

**Variant B comparison (in progress):** grammar trajectory vs A is the key question.

### Week of 2026-06-07 — shopping list

**Strategy:** identify gaps from brain_map, buff them. No fixed epoch counts — run until clusters plateau.

#### 1. Grammar bridge expansion (DeepSeek generation — high priority)
Bridge currently covers only dative double-object verbs (gibt/zeigt/bringt etc.). Missing:

- [x] **Always-dative prepositions** — `mit`, `bei`, `von`, `aus`, `nach`, `zu`, `seit`, `gegenüber`
  - 80 files (235–314). Complete 2026-06-18: `training_data/01_language/bridge/2[3-9][0-9]_bridge_prep*.md`
- [x] **Dative pronouns** — `ihm`, `ihr`, `ihnen`, `mir`, `dir`, `uns`, `euch`
  - 32 files (315–346). Complete 2026-06-18: `*_bridge_datpron_*.md`
- [x] **NOM/ACC isolation** — "der Mann sieht den Jungen" type frames, no dative, to anchor the boundary
  - 20 files (345–364). Complete 2026-06-18: `*_bridge_nomacc_*.md`
  - Generator: `meta/scripts/bridge_extend.py` (NIM primary, OR fallback)
- [x] **Bridge retrofit** — 100 existing bridge files: named chars (Emma/Gran/Taro) → generic NPs
  - Emma → "the girl"/das Mädchen/女の子/那個女孩; Gran → "the woman"; Taro → "the man"
  - Rationale: generic NPs carry explicit morphological case (Das Mädchen gibt dem Jungen > Emma gibt Taro)
  - Complete 2026-06-12: all 100 files rewritten, `---` markers stripped
- [x] **Case-invariance drills** — all 4 cases in one sentence, word order scrambled
  - Core pattern: "Der Mann gibt dem Jungen den Ball des Hundes" (NOM+DAT+ACC+GEN)
  - 120 new files (numbered 101–234 with gaps), 4 languages + Q&A per permutation
  - Complete 2026-06-12: `training_data/01_language/bridge/*_bridge_4case_*.md`
Total addition: 232 files (80 prep + 32 datpron + 20 nomacc + 100 retrofit + existing 4case). Complete 2026-06-18.

#### 2. Arithmetic bridge expansion — COMPLETE (2026-06-18)
Root cause: retrieval framing mismatch (training used multi-modal "Teach me about" format; probe uses "what is X plus Y?").
Solution: compact 4-lingual format — one arithmetic circuit with four linguistic handles per 256-byte window.

- [x] **15 compact multilingual drill files** — `training_data/02_thinking/arithmetic_bridge/c01–c15`
  - c01 identity, c02 same/different, c03 more/less, c04 successor, c05 zero (conceptual foundation)
  - c06 add within 5, c07 add within 10 (all addition facts, both orderings)
  - c08 subtraction as inverse (both directions in same window: "2+2=4. 4-2=2.")
  - c09 comparison, c10 objects addition, c11 objects subtraction (grounded transfer)
  - c12 probe format (80 exchanges — exact brain_map format, 20 facts × 4 langs, no labels)
  - c13 sequences/patterns, c14 rule application (ALeRT-style), c15 contrastive right/wrong
  - Generator: `meta/scripts/arith_gen.py` (NIM primary, OR fallback)
  - Training order: c01 → c15 all `--no-shuffle`; c12 positioned after c01–c11

#### 3. Teaching story annotation — COMPLETE (2026-06-13)
- [x] 5006 teaching stories annotated with `_marked.md` pairs
  - Case-role brackets: `(NOM)` `*verb*` `{ACC}` `[DAT]` `<GEN>` on all 4 language versions
  - Files live alongside originals: `tier_N/.../story_marked.md` — originals untouched
  - Quality scan: 35 leaked-reasoning files identified and re-generated (clean)
  - 1 corrupted source file (`thanking_2.md`) repaired before annotation
  - Final count: 5006/5006 annotated, 0 failures

#### 5. Focused corpus for weekday runs
After variant B finishes (Sunday/Monday):

- [x] Compare grammar μ trajectory A vs B — pick ordering winner
- [x] Build `campaign14c_manifest.txt` — focused on weak clusters:
  - DROP: vehicle files and object files from phase_A (DONE ×3)
  - KEEP: phase_A animal files, phase_B, full grammar block, bridge (expanded), lang_3/4/5
  - KEEP: full teaching stories block (emotions/cognitive/abstract still weak)
  - WEIGHT: grammar block × 2 (repeat it in manifest) if B shows no improvement over A
  - Keep boolean stories (emotions_boolean just hit DONE ×1 — confirm at B-E3 before dropping)

#### 6. Probe set additions
- [x] Add always-dative preposition probes to `language.jsonl`
  - e.g. "Die Frau geht mit" → expect "dem Mann" / "der Frau" etc.
  - ~10 new grammar probes (brings grammar category from 8 → 18 probes for better resolution)

#### 7. Variant B completion (automated) — COMPLETE
- [x] B-E1 scan complete
- [x] B-E2 scan complete
- [x] B-E3 scan complete
- [x] Compare A vs B grammar trajectory — **A wins** (bridge before grammar). See `02_bridge_after_grammar.md` comparison table.

### Material generation — COMPLETE (2026-06-18)

- [x] **Arithmetic Phase B** — 5 paraphrase files (p01–p05): varied question surface, same facts as Phase A
  - p01 add paraphrase, p02 sub paraphrase, p03 count paraphrase, p04 compare paraphrase, p05 word problems
  - Generator: `meta/scripts/arith_gen.py --phase b`
  - Do not train Phase B until Phase A shows stable arithmetic retrieval on brain_map
- [x] **Wiki audit** — 8,443 files at `03_social_cognitive/wiki/`, format clean (0 issues), languages balanced
  - NOTE: git shows these as deleted at old path `03_education/wiki/` — unstaged deletes are expected, not corruption
- [x] **Thinking probes** — `training/corpus_admin/probe_sets/thinking.jsonl` — 94 probes, 14 categories
  - Covers: arithmetic ×4 languages, paraphrase, grounded, identity, comparison, successor, zero,
    sequences, rule application, contrastive, grounded_causal

### Block manifest build (before run)

- [x] Write `meta/scripts/build_campaign14_thinking_manifests.py` — COMPLETE (2026-06-18)
  - Output: `training/corpus_admin/campaign14_blocks/c14_02_arithmetic_bridge.txt` (20 files)
  - Output: `training/corpus_admin/campaign14_blocks/c14_03_grounded_stories.txt` (780 files, EN/DE/JP/ZH consecutive per story)
  - Output: `training/corpus_admin/campaign14_blocks/c14_04_reasoning.txt` (68 files)
  - Combined: `training/corpus_admin/campaign14_thinking_manifest.txt` (868 files total)
  - All 868 paths verified on disk
- [x] Build corpus text files for each thinking block — COMPLETE (2026-06-18)
  - `training/corpus/c14_02_arithmetic_bridge.txt` — 20 files, 56 KB, 0 skipped
  - `training/corpus/c14_03_grounded_stories.txt` — 780 files, 774 KB, 0 skipped (549 whitespace-normalised)
  - `training/corpus/c14_04_reasoning.txt` — 68 files, 124 KB, 0 skipped
  - All three: "All files validated — corpus is clean."

---

## Campaign 15 — Education campaign (03_education)

**Goal:** CKS knowledge grounding on top of language+thinking checkpoint.
**Data:** `training_data/03_education/` — wiki (~8400 files, levels 1–4)
**Corpus:** `training/corpus_admin/campaign16_manifest.txt` exists (418 CKS dialogue files, complete)

### Next steps (after Campaign 14 completes)
- [ ] Decide: wiki files in C15, or keep C15 = CKS dialogues only?
- [ ] Build `training/corpus_admin/probe_sets/thinking.jsonl` (arithmetic + reasoning probes)

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

## CKS Education Pipeline — Campaign 16 prep

**Goal:** Generate `[user]/[Ninereeds]` dialogue `.md` files from the 301-node CKS curriculum.
**Spec:** `training_data/ninereeds_cks_curriculum.md` (v2.2) — read Phases 4 and 5 before starting.
**Status (2026-06-18):** Phases 1–5 complete. Campaign 16 corpus ready.

### Phase 4 — Dialogue generation (DeepSeek) — COMPLETE (2026-06-18)

- [x] Write `meta/scripts/phase4_gen.py`
- [x] Run pilot (10 nodes, mix of domains/grades/languages) and review quality
- [x] Run full generation — 418/418 files, 0 issues after validation passes
- [x] Structural validation pass — all Ninereeds turns end with ?, all tags intact
- Output: `training_data/04_education/dialogues/preschool/{domain}/` and `k8/band_{a,b,c}/{domain}/`

### Phase 5 — Training manifest — COMPLETE (2026-06-18)

- [x] Build `meta/scripts/build_campaign16_manifest.py`
- [x] Manifest: `training/corpus_admin/campaign16_manifest.txt` — 418 files, tier 0→9 order
- [x] Block files: `training/corpus_admin/campaign16_blocks/tier_N.txt` (10 files)
- [x] Verified: all 418 paths exist on disk
- Order: Tier 0 (preschool anchors) → Tier 9 (grade 8); round-robin by domain within tier; preschool nodes en/de/jp/zh consecutively

---

## Standing work (lower urgency)

- [ ] Phase I — Corpus critic (`meta/scripts/corpus_critic.py`) — before any full-scale campaign
- [ ] Phase E — Wiki splitting (for finer curriculum ordering)
- [ ] Phase H — Ordering manifests (depends on Phase E)
- [ ] Fix `allowlist_rank` not propagating into JSONL units (cosmetic; doesn't affect training order)
