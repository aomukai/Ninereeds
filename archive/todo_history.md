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
  - Output: `training/corpus_admin/campaign14_blocks/c14_03_grounded_stories.txt` (2988 files — updated 2026-06-20; was 780)
  - Output: `training/corpus_admin/campaign14_blocks/c14_04_reasoning.txt` (68 files)
  - Output: `training/corpus_admin/campaign14_blocks/c14_05_vignettes.txt` (2048 files — added 2026-06-20)
- [x] Build corpus text files for each thinking block — COMPLETE (2026-06-20)
  - `training/corpus/c14_02_arithmetic_bridge.txt` — 20 files, 56 KB, 0 skipped
  - `training/corpus/c14_03_grounded_stories.txt` — 2988 files, 3.20 MB, 0 skipped (updated 2026-06-20)
  - `training/corpus/c14_04_reasoning.txt` — 68 files, 124 KB, 0 skipped
  - `training/corpus/c14_05_vignettes.txt` — (to build before training run)
  - All three validated: "All files validated — corpus is clean."

### Campaign 14c — COMPLETE (2026-06-20)

**Winner:** `checkpoints/c14c_winner.pt` = `core/c14c_vignettes_e2.pt` (shaped **0.989**, EN 0.996, DE 0.983, JP 0.980, ZH 0.997; brain scan picked E2 over E3: spatial collapse + arithmetic_grounded loss in E3 outweighed grammar gain)
**Report:** `training/logs/campaign_14_reports/03_campaign14c.md`

Block results summary:

| Block | Corpus | Best | Shaped |
|---|---|---|---|
| 1 — arith standalone | 20 files | — | ABANDONED (format saturation) |
| 2 — arith+grounded | 3,008 files | E2 | 0.946 |
| 3 — reasoning+arithB | 73 files | E3 | 0.891 |
| 4 — vignettes | 2,048 files | E3 | **0.990** |
| 5 — education | 418 files | E2 | 0.933 |

Key finding: vignettes training produced raw ≈ shaped (delta ~0.000) — model generates clean text without prompted running-start. ZH 0.998 near-perfect; JP 0.979 weakest; education regressed to 0.933 confirming vignettes E3 as C14c ceiling.

---

## Campaign 15 — Language/Thinking Retrain with EDJC rotation

**Goal:** Retrain the full language+thinking curriculum from `checkpoints/c13_Phase_C_winner.pt`
using the EDJC-rotated corpus. Same block order as C14c winner run; same --no-shuffle discipline.
Language rotation eliminates EN/DE positional advantage over JP/ZH.

**Design rationale:**
- C14c trained from `c14_winner.pt` (already post-language-core). C15 retrains everything from scratch on the rotated corpus to propagate language rotation through Hebbian co-firing from the very first language-core epoch.
- Confirmed EDJC rotation works: C14c Block 4 ZH 0.998 > EN 0.997 — positional bias reversed.

**Base checkpoint:** `checkpoints/c13_Phase_C_winner.pt` (shaped 0.925)

### Corpus files — ALL BUILT (2026-06-20)

| Block | File | Files | Size | Notes |
|---|---|---|---|---|
| 1 — language core | `training/corpus_admin/campaign15_manifest.txt` | 42,021 | ~40 MB | EDJC-rotated; phase_A/B rotated by concept group; lang_1–5 rotated in-place; boolean/philosophy rotated in-place |
| 2 — arith+grounded | `training/corpus/c15_arith_grounded.txt` | 3,008 | 3.25 MB | 20 arith (Phase A + B) + 2988 grounded stories (EDJC manifest) |
| 3 — reasoning+arithB | `training/corpus/c15_reasoning_arithB.txt` | 73 | 0.13 MB | 5 arithB + 68 reasoning (EDJC manifest) |
| 4 — vignettes | `training/corpus/c15_vignettes.txt` | 2,048 | 1.7 MB | Same as c14_05_vignettes.txt (internal rotation) |
| 5 — education | `training/corpus/c15_education.txt` | 418 | 0.6 MB | Same as c14c_education.txt |

Block manifest files: `training/corpus_admin/campaign15_blocks/`

### Launch commands (when ready)

```bash
PYTHON=/home/aomukai/.unsloth/studio/unsloth_studio/bin/python
BASE=checkpoints/c13_Phase_C_winner.pt

# Block 1 — language core (42,021 files, EDJC rotation)
CUDA_VISIBLE_DEVICES=0 nohup $PYTHON train.py \
  --phase 0 \
  --corpus-file training/corpus_admin/campaign15_manifest.txt \
  --output core/c15_language.pt \
  --resume $BASE \
  --epochs 3 --epoch-checkpoints --amp-bf16 --no-shuffle --batch-size 4 \
  > training/logs/c15_language_train.log 2>&1 &
echo "PID: $!"

# Block 2 — arith+grounded (base = best language epoch)
CUDA_VISIBLE_DEVICES=0 nohup $PYTHON train.py \
  --phase 0 \
  --corpus-file training/corpus/c15_arith_grounded.txt \
  --output core/c15_arith_grounded.pt \
  --resume core/c15_language_eK.pt \
  --epochs 3 --epoch-checkpoints --amp-bf16 --no-shuffle --batch-size 4 \
  > training/logs/c15_arith_grounded_train.log 2>&1 &

# Block 3 — reasoning+arithB (base = best arith+grounded epoch)
CUDA_VISIBLE_DEVICES=0 nohup $PYTHON train.py \
  --phase 0 \
  --corpus-file training/corpus/c15_reasoning_arithB.txt \
  --output core/c15_reasoning.pt \
  --resume core/c15_arith_grounded_eK.pt \
  --epochs 3 --epoch-checkpoints --amp-bf16 --no-shuffle --batch-size 4 \
  > training/logs/c15_reasoning_train.log 2>&1 &

# Block 4 — vignettes (base = best reasoning epoch)
CUDA_VISIBLE_DEVICES=0 nohup $PYTHON train.py \
  --phase 0 \
  --corpus-file training/corpus/c15_vignettes.txt \
  --output core/c15_vignettes.pt \
  --resume core/c15_reasoning_eK.pt \
  --epochs 3 --epoch-checkpoints --amp-bf16 --no-shuffle --batch-size 4 \
  > training/logs/c15_vignettes_train.log 2>&1 &

# Block 5 — education (base = best vignettes epoch)
CUDA_VISIBLE_DEVICES=0 nohup $PYTHON train.py \
  --phase 0 \
  --corpus-file training/corpus/c15_education.txt \
  --output core/c15_education.pt \
  --resume core/c15_vignettes_eK.pt \
  --epochs 3 --epoch-checkpoints --amp-bf16 --no-shuffle --batch-size 4 \
  > training/logs/c15_education_train.log 2>&1 &
```

### Status

- [x] Language corpus rotated in-place: boolean_stories, philosophy, lang_1–5 (2026-06-20)
- [x] Separate-language manifests built: grounded_stories, triplet_stories, reasoning (2026-06-20)
- [x] `campaign15_manifest.txt` built: 42,021 files, all paths verified (2026-06-20)
- [x] All C15 thinking corpus files built and validated (2026-06-20)
- [ ] **Launch Block 1 language core** — run train.py with campaign15_manifest.txt
- [ ] Eval after each language epoch; pick best (expect E2 or E3)
- [ ] Launch Block 2–5 in sequence; eval after each epoch
- [ ] Fill training report: `training/logs/` (create c15 folder)
- [ ] Select C15 winner and promote to `checkpoints/c15_winner.pt`

---

## Campaign 16 — Education campaign (03_social_cognitive wiki + 04_education)

**Goal:** CKS knowledge grounding on top of C15 language+thinking checkpoint.
**Data:** `training_data/03_social_cognitive/wiki/` (~8400 files) + `training_data/04_education/`
**Corpus:** `training/corpus_admin/campaign16_manifest.txt` exists (418 CKS dialogue files, complete)

### Gate: is the C15 language foundation ready for education? (decide after C15 Block 4 eval)

**Decision signal:** brain_map multilingual μ after C15 Block 4 (vignettes).

| multilingual μ | Decision |
|---|---|
| ≥ 0.50 | Language foundation ready. Proceed with current education corpus (156 preschool × 4-lang + 262 K-8 × 1-lang). |
| ≤ 0.30 | JP/ZH too weak. Localize K-8 dialogues to 4 languages before C16 launch. |

**If localization needed:**
- Script to write: `meta/scripts/localize_education_k8.py` (same pattern as `localize_philosophy.py`)
- Input: `training_data/04_education/dialogues/k8/` (262 files)
- Output: `*_DE.md`, `*_JP.md`, `*_ZH.md` alongside each EN file
- Prompt design: "localise naturally" — include anti-calque examples for domain terms (photosynthesis, fractions, civic systems) in JP/ZH
- Corpus impact: 262 × 4 = 1,048 files (up from 262); total education corpus 1,360 files (up from 418)
- Also check: whether question-forming (`?` in Ninereeds turns) appears in probe.py output after C15 — if not, a small question-generation drill corpus may be needed before C16

### Next steps (after C15 completes)
- [ ] Run multilingual μ gate above — decide 4-lingual K-8 or proceed as-is
- [ ] Decide: wiki files in C16, or keep C16 = CKS dialogues only?

---

## Campaign 16 design — three key experiments (2026-06-02, details TBD)

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

## Corpus expansion — vignettes (2026-06-19)

**Goal:** Add sentence-rotation vignettes to `training_data/01_language/vignettes/` as a new
language curriculum layer. Each file shows one event from 5 syntactic/lexical angles in 4
languages. Language order rotates per file (EDJC/DJCE/JCED/CEDJ) to prevent positional bias
and counteract EN/DE weight dominance over JP/ZH.

**Rationale:** Epoch saturation (~3 epochs) with WEAK grammar/movement clusters suggests the
existing data is insufficient in *variety of situation* (effective count is files÷4 across
languages). Paraphrase rotation within a single training window forces Hebbian circuits to
extract the semantic invariant rather than the surface form.

**Format:** bare sentence blocks, no [user]/[Ninereeds] tags. 5 blocks × 4 lines each.
**Verb types:** ditransitive (active/bekommen-pass/werden-pass/topicalization/wem-question)
               transitive (active/passive/topicalization/resultative/perspective-shift)
**Vocabulary:** not restricted to allowlist — richer variety is the point.

- [x] Generator written: `meta/scripts/vignette_gen.py`
- [x] Jobs planned: 2920 files (1100 ditransitive, 1820 transitive; 730 per language rotation)
- [x] Audit script written: `meta/scripts/vignette_audit.py` (NIM primary, OR fallback; runs concurrently)
  - Scene graph reconstruction per block, then 8-category check (event, roles, lexical drift, grammaticality ×4, naturalness ×4, German cases, question consistency, language ID)
  - Results: `_audit.jsonl` (one record per file, resumable); failures: `_audit_failures.txt`
- [x] Generation complete: `training_data/01_language/vignettes/v_0001.md` … `v_2920.md` (2920/2920, 2026-06-19)
- [x] Audit + regeneration complete (2026-06-20): **2048 PASS / 872 FAIL (stopped here)**
  - Iterated: lexical-variant Block 4 → tightened synonym constraint → resultative frame
  - Resultative: same verb + outcome phrase (e.g. "cut into pieces", "chased away")
  - Final pass: 70% pass rate. 872 FAIL files deleted. 2048 clean files kept.
  - Block manifest: `training/corpus_admin/campaign14_blocks/c14_05_vignettes.txt` (2048 paths)
- [ ] Add vignettes to campaign14c manifest and test block run (brain_map grammar μ before/after)

Commands:
```
# generation (OpenRouter)
python3 meta/scripts/vignette_gen.py plan          # rebuild jobs if needed
python3 meta/scripts/vignette_gen.py gen --workers 4
python3 meta/scripts/vignette_gen.py verify --fix
python3 meta/scripts/vignette_gen.py status

# audit (NIM primary — runs concurrently with generation)
python3 meta/scripts/vignette_audit.py gen --workers 4
python3 meta/scripts/vignette_audit.py status
python3 meta/scripts/vignette_audit.py report
python3 meta/scripts/vignette_audit.py report --fail-only
```

---

## Corpus expansion — grounded stories scale-up (2026-06-19)

**Goal:** Expand `training_data/02_thinking/grounded_stories/` from 195 stories (780 files)
to 750 stories (~3000 files). Same world, same format — story groups ("monster of the week"),
each self-contained, no strict sequence required.

**Sequencing: vignettes must finish generating first. Story prose generation runs after.**

### World expansion

**New characters:**
- Mei (ZH: 梅) — friend with cat Dou (ZH: 豆). Nearby. Practical, precise. DE=Mei, JP=メイ
- Yun (ZH: 云) — Mei's grandmother. Saturday market stall. Fast hands, sharp eyes.
- Riku (JP: 陸) — postman. Red bicycle. Knows everyone's name.
- Stefan (DE) — police officer. Slow beat. Nods. Badge catches sun.
- Hana (JP: 花) — baker. Open before dawn. Flour always on apron.
- Owen (EN/Welsh) — farmer. Sheep field by meadow path. Big hands. Few words.
- Clara (neutral) — schoolteacher. Careful letters, nature table, calls on quiet children.
- Vern (DE, short for Verner) — carpenter. Side street. Shows by doing. Names every tool.
- Dr. Lena (DE/Scandi) — vet (named, was unnamed in bible).
- Dr. Anand (South Asian) — doctor (named, was unnamed in bible).

**New locations:** The Mill (Mei's family), Vern's Workshop, The Hill, The Root Cellar.

**World bible updated:** `training/corpus_admin/grounded_stories/world_bible.md`
**gen_stories.py updated:** STORIES_DIR path fixed, CAST/CHAR_MAP/CHAR_NAMES/LANG_INSTRUCTIONS extended.

### Story groups (stories 196–750)

| Group | Location/theme | Stories | IDs |
|---|---|---|---|
| the_mill | The Mill | 55 | 196–250 |
| verns_workshop | Vern's Workshop | 50 | 251–300 |
| the_market | Village market stall | 45 | 301–345 |
| the_hill | The Hill | 45 | 346–390 |
| root_cellar_kitchen | Root Cellar / kitchen | 50 | 391–440 |
| dogs_and_cat | Animal behaviour, new places | 40 | 441–480 |
| school_extended | Schoolyard / classroom | 45 | 481–525 |
| village_life | Village street, lane | 65 | 526–590 |
| old_places_new | Oak/Pond/meadow, new angles | 110 | 591–700 |
| education_grounded | CKS concepts shown through action | 50 | 701–750 |

Education-grounded group anchors 24 preschool/KG concepts (forces, lifecycles, sorting,
patterns, community helpers, goods/services, needs/wants, emotions, cooperation, etc.)
by showing them through physical action — never stating them. Double-dips with Campaign 16.

### Status

- [x] World bible extended (`training/corpus_admin/grounded_stories/world_bible.md`)
- [x] `gen_stories.py` updated (path fix, new CAST, CHAR_MAP, CHAR_NAMES, LANG_INSTRUCTIONS)
- [x] Storylist generator written: `meta/scripts/storylist_gen.py`
- [x] Storylist entries generated: stories 196–750 (750 total, all 10 groups complete 2026-06-20)
  - Log: `training/logs/storylist_gen_run.log`
- [x] Vignettes complete — prose generation unblocked (2026-06-20)
- [x] `gen_stories.py` updated: DeepSeek direct primary, NIM + OR fallback (same `_sources()` pattern)
- [x] Prose generation complete (2026-06-20): 2988 files (747 stories × 4 langs)
  - Stories 688–690 excluded: specs missing from storylist (old_places_new batch generation gap; duplicated 666–668 instead). Negligible — 747/750 complete.
  - Log: `training/logs/gen_stories_run.log`
- [x] Build grounded stories manifest block (2026-06-20): `training/corpus_admin/campaign14_blocks/c14_03_grounded_stories.txt` (2988 paths)
- [x] Rebuild corpus text (2026-06-20): `training/corpus/c14_03_grounded_stories.txt` — 2988 files, 3.20 MB, 0 skipped

Commands:
```
python3 meta/scripts/storylist_gen.py status          # check spec generation
python3 meta/scripts/storylist_gen.py gen             # resume if interrupted
python3 meta/scripts/gen_stories.py gen --lang EN,DE,JP,ZH --workers 6  # prose (after vignettes)
python3 meta/scripts/gen_stories.py report --lang EN,DE,JP,ZH           # progress check
```

---

## Standing work (lower urgency)

- [ ] Phase I — Corpus critic (`meta/scripts/corpus_critic.py`) — before any full-scale campaign
- [ ] Phase E — Wiki splitting (for finer curriculum ordering)
- [ ] Phase H — Ordering manifests (depends on Phase E)
- [ ] Fix `allowlist_rank` not propagating into JSONL units (cosmetic; doesn't affect training order)
