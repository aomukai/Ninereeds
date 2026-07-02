# Curriculum Topology

A structured reference of the Ninereeds corpus, training history, and open
research questions. Useful as a briefing document for deep research tools
(GPT Deep Research, Gemini Deep Research) to generate curriculum ordering
proposals, and as a living record of what has been learned so far.

Last updated: 2026-06-23

Status note, 2026-07-01: this file is historical research evidence. It still records
what the corpus campaigns taught us, but it is no longer the active training procedure.
The current procedure is MSM session training; see `training/pipeline/training.md`.

---

## The core research question

Transformer training laws (scaling laws, loss curves, data-to-parameter ratios)
do not apply to BDH. Ninereeds is Hebbian-trained: learning is local and
associative, not gradient-based. There is no established prior art for this
training regime at this scale with this curriculum structure.

The mission is to discover what laws govern BDH training. Every campaign is an
experiment toward that goal, not just a training run.

**Loss curves are unreliable as the primary evaluation signal.** Predicting the
next token correctly measures surface-form compliance, not concept formation.
The shaped score measures format fidelity and vocabulary recall — both are useful
diagnostics but neither tells you whether the model *understands* what it is
producing. The activation map has already demonstrated this gap: in C14c, shaped
score selected E3 as block winner (0.990 vs 0.989); brain scan overturned it
because E3 had lost half its arithmetic_grounded circuit and suffered spatial
after-hub collapse.

**The evaluation stack, highest to lowest priority:**
1. **Brain map** — which concepts formed coherent circuits? After-hub similarity
   is the key metric: higher = more dedicated, less hub-dependent activation.
   Hub count, per-category semantic neuron count, and after-hub μ are all read
   before a checkpoint is promoted.
2. **Shaped score** — useful as a regression gate; not a measure of understanding.
   Report per-language breakdown (EN/DE/JP/ZH) from the 4-lingual eval (72 prompts).
3. **Raw score** — secondary to shaped, confirms format isn't artificially inflating.
4. **Training loss** — dead last. It has very little to do with what we are testing
   for. Report only if a clear anomaly appears.

**Do not promote a checkpoint as block winner without brain_map evidence.**

---

## Corpus inventory (as of 2026-06-23)

The corpus is organised into two sections: the multilingual legacy corpus (C13–C15) and the
EN-only redesign corpus (C16+). Training order for legacy: 01 → 02 → 03 → 04 → 05.

```
training_data/
  01_language/
    phase_A/            6,464 files — concrete anchors (objects, nature, basic properties)
                        4 language variants per concept (EN / DE / JP / ZH)
    phase_B/            4,912 files — agents & social (was phase_C in old numbering)
    teaching_stories/   10,012 files — tier_1/ through tier_4/; narrative grounding
                        5,006 stories × ~2 variants; domain buckets per tier
    boolean_stories/    800 files — yes/no observable-state questions; 4-lang pairs
    triplet_stories/    5,380 files — 1,345 EN × 4 langs, tier 1–4
                        13 categories: abstract_concepts, animals_and_nature,
                        body_and_health, food_and_meals, home_and_daily_life,
                        language_and_grammar, math_and_science, people_and_relationships,
                        play_and_games, school_and_learning, tools_and_making,
                        vehicles_and_travel, weather_and_seasons
    lang/
      lang_1/           5,147 files — one file per allowlist word; EN/DE/JP/ZH
      lang_2/           6,837 files — semantic frames (adj/adv/noun/pronoun/combo)
      lang_3/           615 files — flat dir; reflexive, benefactive, dative, parallel
      lang_4/           316 files — flat dir; spatial location, movement, instrument, stories
      lang_5/           192 files — flat dir; Q&A pairs (wer/wen, wo/wohin, when, why, how, yn/doch)
    grammar/            1,800 files — 11 modules; numeric subdirs = training order
    bridge/             352 files — surface-form pre-loading + 4-case drills
  02_thinking/
    arithmetic_bridge/  77 files — legacy counting + Phase A compact drills + Phase B paraphrase
    grounded_stories/   2,988 files — 747 stories × 4 langs; sequential — do NOT shuffle
    reasoning/          68 files — arithmetic, logic, epistemic uncertainty
  03_social_cognitive/
    wiki/               8,443 files — EN/DE/JP/ZH balanced; long-form encyclopedic Q&A; levels 1–4
  04_education/
    dialogues/          418 files — CKS K-8 corpus; preschool/ and k8/band_{a,b,c}/
  05_philosophy/        144 files — Socratic dialogues; 4 languages; flat dir

  redesign/words/       66,536 files (EN-only redesign corpus, C16+)
    28 semantic buckets: actions, animals, body, clothing, cognition, colors,
    communication, emotions, events, food, household, language, materials,
    movement, nature, people, places, processes, properties, quantities,
    shapes, social, sounds, space, states, technology, time, tools
    Each concept has angle files (what_is, meaning, example, boundary_*, etc.)
    and a _rephrase sibling per angle (C16A pass complete as of 2026-06-23).
    Largest buckets: actions (10,494), properties (7,425), household (3,450).
    33,268 source files × 1 rephrase = 33,268 + 33,268 = 66,536 files.
    Generator: meta/scripts/angle_gen.py | Augmentor: meta/scripts/angle_aug.py
```

**Legacy corpus total: ~55,000 files**
**Redesign corpus total: ~66,500 files**
**Combined: ~121,500 files**

---

## Corpus roles and design intent

### Phase A — concrete anchors
- Format: `[user]`/`[Ninereeds]`, 4 block pairs per file
- Question forms: what does X look like / where is X found / what happens to X / what does X do
- Response: 5 property lines + 1 summary, no pronouns, no negation, one sentence per line
- Content: objects, nature, body, basic properties — anything with a static visual referent

### Phase B — agents & social
- Same format as Phase A
- Question forms: what is X-ing / when does X happen / what does X bring / what does X give
- Content: social concepts, agent roles, relational knowledge

### Teaching stories
- Format: `[user]`/`[Ninereeds]`, 4 language blocks (EN→DE→JP→ZH)
- Tiers 1–3: 1 pair per language; Tier 4: 2 pairs per language
- Omniscient narrator, no named characters, village world setting
- Content: all ~5,000 vocab words; tier-1 words (B/D/E) get anchor stories first
- Boolean subset (800 stories): elimination structure (wrong guess → No; correct → Yes)
  teaches yes/no discrimination through observable evidence

### Grounded stories
- Plain prose narrative, no `[user]`/`[Ninereeds]` tags
- Canon cast: Emma, Taro, Gran, Biscuit, Bello (introduced gradually from story 48)
- Expanded from 195 → 747 stories (2,988 files); new cast members, locations, groups added in C14c
- 12+ locations; curriculum blocks: spatial → temporal → causal → two-dog → arithmetic
- Must NOT be fed as a contiguous block (catastrophic forgetting confirmed, run 2)
- Must interleave at ~0.5% of corpus; arithmetic bridge prepended at ≤2% worked cleanly

### Triplet stories
- Format: `[user]tell me a story about X` → `[Ninereeds]` narrative response
- Single block per file (one language per file); 4 separate files per story (EN/DE/JP/ZH)
- Tier 1: picture-book level; Tier 4: extended paragraph, named characters
- **Design intent:** vocabulary reinforcement between lang and wiki.
  Teach the word in lang_1, see it used naturally in a triplet story, then deepen via wiki.
- **Integration question:** triplets may be most effective interleaved during teaching story
  training, not as a separate block — see curriculum ordering section below.

### Vignettes (c14_05)
- Format: 5 syntactic rotations of the same event × 4 languages per file (2,048 files)
- Language order rotates across files using EDJC/DJCE/JCED/CEDJ cycle — prevents positional bias
- **Purpose:** force Hebbian circuits to extract the semantic invariant (same event, varied
  surface form) rather than memorise surface form
- **C14c result:** vignettes pushed shaped to 0.990 peak; raw ≈ shaped (delta ~0.000) throughout —
  the model generates clean text without a prompted running-start
- EDJC rotation confirmed to eliminate EN/DE positional advantage: ZH 0.998 > EN 0.997 at peak

### Grammar corpus
- Function-first, case-aware German spine
- Numeric cluster order = intended training order
- Tests: dative (static), accusative (movement), genitive, V2 word order, ditransitive
- **Timing question:** introduce after semantic substrate; bridge used as corrective layer after grammar

### Arithmetic bridge
- Two phases: Phase A (compact 4-lingual Peano-ordered drills, c01–c15) and Phase B (paraphrase
  equivalence — same facts, varied question surface, p01–p05)
- **Arithmetic saturation rule (confirmed C14c):** never run arithmetic as a standalone pass at
  <100 files × 3 epochs. 20 files alone collapsed shaped 0.934 → 0.863 and bled arithmetic tokens
  into all narrative completions. Fix: prepend arith at ≤2% of grounded stories block.

### Wiki
- 4 levels, broader concept knowledge than phases; child-facing explanatory language
- Level 1–2 probably precedes triplet tiers 3–4; Level 3–4 follow

### Education dialogues
- CKS K-8 curriculum; conversational register; question-forming, explanatory completions
- Improves conversational register but regresses shaped score from vignettes peak
- Use as a specialist block after vignettes, not as a replacement for vignettes

---

## Empirical findings by campaign

### Campaigns 1–12 (runs 1–12)

**Format compliance dominates volume.** Small well-formed files outperform
oversampling. The shaped score is highly sensitive to `[user]`/`[Ninereeds]`
format fidelity — malformed files have outsized impact at this model size.

**Epoch sweet spot.** Run 4 identified an optimal epoch count beyond which the
model overfits to surface form. Run 3 epochs; pick winner from brain scan.

**Scaling ablation (runs 10–12).** 25M → 151M → 604M. Per-layer weights at 151M
opened capability headroom. 604M showed capacity but needed more data to fill it.
The 25M model is used for fast validation.

**4-lingual beats English-only.** Multilingual training from the start outperforms
English-only + later localisation.

### Campaign 13 — Bridge → Phase A → Phase C (now Phase B)

**Result:** shaped 0.925. Best checkpoint: `checkpoints/c13_Phase_C_winner.pt`.

**Bridge as kickstarter (+0.007):** Bridge → Phase A beats Phase A alone.
**This reading is wrong — see corrected interpretation below.**

**Bridge as connector (−0.008 to −0.018):** Inserting bridge between phases
consistently hurts. This finding still holds.

**Phase A + Phase B absorb cleanly.** 0.925 is the ceiling for this curriculum.

**B/D/E permanently fail (4 attempts each).** Emotions, cognitive verbs, and
abstraction do not absorb in the static property-listing format.

### Corrected interpretation of Bridge-as-kickstarter (2026-06-02)

Bridge introduces connective vocabulary surface forms before there is any semantic
substrate. The model learned to produce these words in the correct positions in the
training format — improving format compliance and shaped score — without forming
semantic associations. **Corrected role:** bridge is a corrective layer, not a
warm-up. Use it after Phase A + Phase B + stories have run and been probed.

### Campaign 14a — Full language curriculum

**Base:** `checkpoints/c13_Phase_C_winner.pt` (0.925)
**Order:** phase_A → phase_B → lang_1/2 → bridge → grammar → lang_3/4/5 → teaching+triplets → boolean

| Epoch | Shaped | Notes |
|---|---|---|
| E1 | 0.928 | Boolean format bleeding into all probes at E1 |
| E2 | **0.930** | Peak — new high |
| E3 | 0.917 | Regression |

Best: `core/campaign14_full_e2.pt` (0.930)

### Campaign 14b — Bridge-after-grammar variant

**Base:** `checkpoints/c13_Phase_C_winner.pt` (0.925)
**Order:** phase_A → phase_B → lang_1/2 → grammar → lang_3/4/5 → **bridge** → teaching → boolean
(bridge moved after grammar rather than before, acting as corrective consolidation)

| Epoch | Shaped | Notes |
|---|---|---|
| E1 | **0.934** | New high; tighter floor (0.80 worst) |
| E2 | 0.934 | Tied shaped; worse floor (0.75 worst prompt) |
| E3 | 0.917 | Regression |

Best: `core/campaign14b_full_e1.pt` → promoted to `checkpoints/c14_winner.pt` (0.934)
Tiebreaker over E2: worst-prompt floor 0.80 vs 0.75. Bridge-after-grammar confirmed better than bridge-before.

### Campaign 14c — Vignettes + Grounded scale-up

**Base:** `checkpoints/c14_winner.pt` (0.934)
**New corpus:** grounded stories expanded 195→747 (2,988 files); vignettes block (2,048 files)
**First campaign with 4-lingual eval** (72 prompts = 18 slots × EN/DE/JP/ZH)

#### Block 1 — Arithmetic standalone — ABANDONED
20 arith files × 3 epochs = 100% arithmetic saturation. Shaped 0.934 → 0.863–0.867.
Arithmetic tokens bled into all narrative completions. **Rule confirmed:** ≤5% interleave only.

#### Block 2 — Arith+Grounded (arith at 1.6% of block)

| Epoch | Shaped | Notes |
|---|---|---|
| E1 | 0.940 | New high; story character bleed (Yun/Mei) — normal E1 |
| **E2** | **0.946** | New high; floor lifted to 0.91 |
| E3 | 0.938 | Regression |

Winner: `core/c14c_grounded_e2.pt` (0.946)

#### Block 3 — Reasoning + ArithB (73 files)

| Epoch | Shaped | Notes |
|---|---|---|
| E1 | 0.828 | Big regression; Q&A format floods narrative completions |
| E2 | 0.872 | Recovery |
| **E3** | **0.891** | Best; floor 0.79 on 'Language' |

Winner: `core/c14c_reasoning_e3.pt` (0.891)

#### Block 4 — Vignettes (2,048 files) — first 4-lingual eval

| Epoch | Shaped | EN | DE | JP | ZH | Notes |
|---|---|---|---|---|---|---|
| E1 | 0.989 | 0.996 | 0.978 | 0.986 | 0.996 | Raw=shaped (delta 0.000) |
| **E2** | 0.989 | 0.996 | **0.983** | 0.980 | 0.997 | DE improving; brain-scan winner |
| E3 | 0.990 | 0.997 | 0.985 | 0.979 | 0.998 | Higher shaped; spatial circuit collapse |

Brain scan overturned E3 as winner: E3 had spatial after-hub collapse (0.224→0.144, −36%) and
lost half the arithmetic_grounded circuit (1,021→528 neurons). **E2 selected as winner.**

Brain scan comparison (E2 vs E3):

| Dimension | E2 | E3 | Better |
|---|---|---|---|
| Spatial after-hub | **0.224** | 0.144 | **E2** |
| emotions_boundary after-hub | **0.378** | 0.229 | **E2** |
| arithmetic_grounded neurons | **1,021** | 528 | **E2** |
| arithmetic_zh after-hub | **0.915** | 0.869 | **E2** |
| arithmetic_jp after-hub | **0.912** | 0.895 | **E2** |
| Language semantic neurons | 2,985 | 3,751 | E3 |
| Grammar dedicated neurons | 814 | 1,212 | E3 |

Winner: `core/c14c_vignettes_e2.pt` (shaped 0.989, EN 0.996, DE 0.983, JP 0.980, ZH 0.997)

#### Block 5 — Education (418 files)

| Epoch | Shaped | EN | DE | JP | ZH |
|---|---|---|---|---|---|
| E1 | 0.931 | 0.912 | 0.939 | 0.932 | 0.940 |
| **E2** | **0.933** | **0.949** | 0.938 | 0.914 | 0.932 |
| E3 | 0.926 | 0.933 | 0.949 | 0.898 | 0.925 |

Education improved conversational register but regressed shaped from vignettes peak (0.990→0.933).
JP most fragile. Vignettes E2 is the C14c performance ceiling.

**C14c winner: `checkpoints/c14c_winner.pt`** (promoted from `core/c14c_vignettes_e2.pt`)

### C14c key findings

1. **Vignettes breakthrough:** shaped 0.990 peak; raw ≈ shaped throughout (delta ~0.000). Model
   generates clean format without prompted running-start.
2. **EDJC rotation:** language order cycling (EDJC/DJCE/JCED/CEDJ) eliminated EN/DE positional
   advantage. ZH 0.998 > EN 0.997 at peak — language order advantage neutralised.
3. **Brain scan overturned shaped-score pick:** E3's 0.001 shaped advantage masked spatial circuit
   collapse. Brain scan is now mandatory before winner selection.
4. **After-hub similarity:** key metric. Higher = more dedicated circuits (less hub-dependent).
   This is the single most useful number when comparing checkpoints.
5. **Arithmetic saturation confirmed:** standalone arith collapsed shaped 0.934→0.863. Fixed
   by prepending at ≤2% of grounded block.
6. **Grounded scale-up worked:** 195→747 stories pushed shaped 0.940→0.946 at E2. 4× more
   stories, new locations/characters improved causal reasoning and multilingual coverage.

### Activation-geometry scan — C13 winner (2026-06-02, v1 probes)

First activation scan using 180 probes across 13 concept categories. Full methodology and
corrected interpretation: `docs/brain_map.md`.

**Corrected findings:** prompt-template confounds made several initial findings unreliable.
EN/DE within-language template similarity was mistakenly read as cross-language concept alignment.
"87% silent" means not activated by this probe battery, not unused globally.

**What remains valid:**
- The scanner works as a prompt-family discriminator
- Hub structure is real (causal role unconfirmed)
- Construction-specific grammar probes needed; aggregating case categories is misleading
- Grammar corpus timing question (after semantic substrate) still supported

### Brain map v2 (current)

Two probe sets, run after every epoch on every block:
- `training/corpus_admin/probe_sets/language.jsonl` — 104 probes, 16 categories
- `training/corpus_admin/probe_sets/thinking.jsonl` — 94 probes, 14 categories
  - Categories: arithmetic (EN/DE/JP/ZH), arithmetic_para, arithmetic_grounded, identity,
    comparison, successor, zero, sequence, rule_application, contrastive, grounded_causal

Hub detection threshold: 0.7. **Key output to read:** after-hub similarity per category —
the coherence of each circuit once shared hub neurons are removed.

---

## Campaign 15 results

**C15 is the full language + thinking retrain** from scratch (base: `checkpoints/c13_Phase_C_winner.pt`).

Motivation: C14's language block lacked EDJC rotation and 4-lingual eval. C15 rebuilds the
language foundation with the full rotated corpus (42,021 files) and stacks thinking blocks.
Blocks 2–5 ran autonomously via `meta/scripts/c15_pipeline.py`.

| Block | Corpus | Files | Winner | arith_jp | Shaped |
|---|---|---|---|---|---|
| 1 — Language core | `campaign15_full.txt` | 42,021 | E2 | **0.987** | 0.958 |
| 2 — Arith+Grounded | `c15_arith_grounded.txt` | 779 | E1 | 0.984 | 0.976 |
| 3 — Reasoning/ArithB | `c15_reasoning_arithB.txt` | 73 | E1 | 0.990 | 0.941 |
| 4 — Vignettes | `c15_vignettes.txt` | 2,048 | E1 | 0.937 | 0.987 |
| 5 — Education | `c15_education.txt` | 418 | **E1** | **0.9994** | 0.920 |

**C15 winner: `checkpoints/c15_education_winner.pt`** (promoted from `core/c15_education_e1.pt`)

### C15 key findings

**EDJC rotation confirmed at language-block stage.** arith_jp hit 0.987 at B1 E2 —
above C14c's 0.912 peak which came 4 blocks later. Rotation benefit is front-loaded.

**E1 winner pattern for focused blocks.** Blocks 2, 3, 4 all picked E1. Only the
large full-curriculum block (B1, 42k files) peaked at E2. Rule: if the block is
< ~1000 files, expect E1 to be the winner.

**Vignettes compress arithmetic circuits per epoch.** arith_jp trajectory at B4:
E1=0.937 → E2=0.860 → E3=0.781. Three epochs of syntactic rotation actively compresses
arithmetic circuits. **For C16: run vignettes for 1 epoch only.**

**B3 rule_application spike at E2** (0.921 vs E1's 0.788) confirmed reasoning corpus
works as intended, but arithmetic_jp cost (−0.009) made E1 the winner. This trade-off
is inherent: reasoning corpus improves rule circuits but compresses arithmetic-jp.

**Automated pipeline ran blocks 2–5 unattended.** OOM issue on B3 required manual
intervention (batch=1, adam8bit, PYTORCH_ALLOC_CONF=expandable_segments:True) due to
desktop game (mnm.exe) consuming 7.4 GB VRAM. Fix is now embedded in the pipeline.

**B5 (Education) restored arith_jp to campaign peak.** After vignettes compressed
arith_jp from 0.990→0.937, the K-8 EN-only corpus restored it to 0.9994 — the highest
arith_jp in any C15 block. The education corpus is arithmetically compatible. Shaped
fell to 0.920 (from 0.987) because K-8 is EN-only and shaped is 4-lingual weighted.
The shaped cost is the price of arith_jp recovery.

---

## Campaign 16 — Concept anchoring (EN-only redesign)

**Motivation:** C13–C15 peaked at E2–E3. Hypothesis: the 25M model's capacity is
consumed by multilingual surface disambiguation before forming semantic concept clusters.
C16 tests EN-only + semantic bucket ordering + identity interleaving to find the correct
recipe before reintroducing language complexity.

**Base:** fresh init (no prior checkpoint)
**Corpus:** `training/corpus/redesign_c16.txt` — 34,645 files (33,966 concept + 679 identity insertions)
**Probe set:** `c16_concepts.jsonl` — 60 probes, 10 categories

| Epoch | Shaped | Flags | Chat (12q) | Winner |
|---|---|---|---|---|
| E1 | 0.995 | 2 | — | |
| E2 | 1.000 | 0 | "I am Ninereeds." | |
| E3 | 0.998 | 3 | 5/12 | |
| **E4** | **0.996** | **0** | **9/12** | **★** |
| E5 | 0.995 | 1 | 8/12 | |

E5 triggered STOP: 2/3 signals regressed simultaneously. **Winner: `checkpoints/c16_concept_anchoring_winner.pt`**

### C16 after-hub scores (E4 winner)

| Category | E4 after-hub | Notes |
|---|---|---|
| boundary | 0.409 | Strongest — "I don't know" refusal crystallised first |
| household | 0.542 | Strongest semantic cluster — distinct physical properties |
| animals | 0.272 | Second strongest semantic cluster |
| colors | 0.220 | Small but clean |
| identity | 0.141 | Behaviourally solid, structurally routed through hubs — fragile |
| nature | 0.104 | Weak — water-concept blur |
| body | 0.158 | Weak |
| emotions | 0.064 | Weak — abstract, no grounding |
| actions | 0.051 | Weak — agent-first framing bleeds into people/animals |
| food | 0.078 | Weak — inconsistent "X is food" spine |

### C16 key findings

1. **EN-only + semantic bucket ordering extends learning to E4.** Prior campaigns peaked
   at E2–E3. The recipe (EN-only, bucket-ordered, identity every 50 files, multiple angles)
   is confirmed correct for this model size.
2. **Hebbian learning favours physically distinct objects.** Household (0.542) and animals
   (0.272) form strong clusters. Abstract categories (emotions=0.064, actions=0.051) fail
   to cluster — they need structural spine reinforcement, not more volume.
3. **Category spine is the key variable, not file count.** Household's consistent "X is
   furniture" spine → strong cluster. Food's mixed "X is food" / "X is a seed" spine →
   weak cluster (0.078). Volume does not compensate for inconsistent anchoring.
4. **Boundary crystallises first.** The refusal pattern ("I don't know") forms the most
   stable circuit. It is structurally simple and appears in every file.
5. **Identity is behaviourally correct but structurally hollow.** Routed through general
   hubs, not dedicated neurons. Needs reinforcement to survive further training.

---

## Campaign 16A — Question-surface rephrase pass

**Base:** `checkpoints/c16_concept_anchoring_winner.pt`
**Goal:** Break surface-form lock on weak categories. Same concept facts, varied question
wording. One `_rephrase.md` sibling per source angle file.

**Corpus:**
- Source: 33,268 angle files across 28 semantic buckets in `training_data/redesign/words/`
- Rephrase: 33,268 `_rephrase.md` files generated via `angle_aug.py --wave 1`
- Generator: OpenRouter + DeepSeek + NVIDIA in parallel (per-worker claim files)
- Completed: 2026-06-23

**Corpus cleanup performed before training:**
- 660 trash files deleted (numbered duplicates: person_3–12, assembling_3/4, etc.; fake words:
  attentioning, sud, everydaying, today-you)
- ~336 compound-phrase artifact files deleted (thirsty bird, body that has slept, bowl of soup, etc.)
- All ~2,730 `unsorted/` concepts re-bucketed via DeepSeek classification into 28 named buckets
- 3 new buckets created: events, processes, technology (sounds already existed, now populated)
- 79 bad rephrases regenerated (USER_UNCHANGED or missing); 3 format violations fixed

**Validation:** `meta/scripts/validate_aug.py` — 33,268/33,268 rephrase files, 0 missing,
0 USER_UNCHANGED failures. 312 NEAR_COPY flags are false positives (short files, question
rephrased but answer correctly unchanged).

**Signal to watch:** do emotions/actions/food after-hub scores recover? Does identity cross 0.25?

---

## C16B — Structural supplement pass (planned)

Target weak categories with explicit spine files (see `claude/project_c16b_supplements.md`):
- **Food spine:** every food concept gets "X is food. People eat X." anchoring
- **Nature spine:** "X is part of nature." + distinguishing feature early
- **Emotions:** situation-grounded examples ("A child gets a toy. The child feels happy.")
- **Actions:** anchor the action first, agents second ("Running is an action. A person can run.")
- **Boundary/negation:** non-living false-premise questions use negation, not "I don't know"

File naming: `concept_angle_supplement.md` + `_supplement_rephrase.md`. Additive — never
overwrites originals. Train from best C16A checkpoint.

---

## Known failure modes

**B/D/E absorption failure** — emotions, cognitive verbs, abstraction do not land
in the static property format. Teaching stories are the intervention.

**Bridge mistiming** — bridge as a cold-start primer teaches surface forms without
semantic substrate. Shaped score improves; understanding does not. Bridge belongs
after the semantic substrate is probed and confirmed.

**Arithmetic saturation** — standalone arith at <100 files × 3 epochs collapses
shaped score and bleeds arith tokens into narrative completions. Fix: ≤2% interleave.

**Reasoning format bleed** — Q&A format of reasoning corpus competes with narrative
completions. Same root cause as arithmetic saturation. Block 3 of C14c dropped shaped
from 0.946 to 0.828 at E1 before recovering to 0.891 at E3.

**Dative instability** — many conflicting activation patterns for the same case
relationship. Needs stable semantic substrate before grammar corpus can resolve it.

**Book loop** — repetitive generation under sustained output pressure. Minimised
by loop count gate in shaped score.

**JP fragility** — Japanese degrades first under format competition (education block
regression: 0.914→0.898). Persistent weakest language across most blocks.

**Catastrophic forgetting (stories as block)** — confirmed run 2. Must interleave
at ~0.5% of corpus.

**Corpus manifest vs corpus file** — `train.py` reads `--corpus-file` as raw bytes.
Passing a manifest (list of file paths) trains on file path strings, not content.
Always build the corpus with `build_training_corpus.py --order-file` before training.

---

## Curriculum ordering hypothesis (current)

Based on C13 findings, C14a/b/c experiments, and brain-map evidence:

```
Phase A (concrete anchors)
  → Phase B (agents & social)
  → lang_1/2 (vocabulary)
  → grammar (case structure)
  → lang_3/4/5 (complex constructions)
  → bridge (corrective — after grammar, not before)
  → teaching stories + boolean (narrative grounding for B/D/E)
     interleaved with triplets (aligned by category, tier 1–2 first)
  → PROBE — brain_map (after-hub per category) + eval
     confirm clusters are clean before proceeding
  → grounded stories (arith prepended at ~2%)
  → reasoning (Q&A format — expect E1 regression, recover by E3)
  → vignettes (syntactic rotation — EDJC cycle)
  → wiki (broader concept knowledge)
  → triplets tier 3–4 + wiki level 3–4 (interleaved)
  → education (conversational register — optional specialist block)
  → philosophy (Socratic dialogues — late stage)
```

The probe checkpoint before bridge is not optional.

**Open ordering questions:**

1. **Teaching stories + triplets: interleaved or sequential?** Interleaving is the
   hypothesis; sequential is the control. Untested as of C15.
2. **Grounded stories: before or after teaching stories?** Grounded stories establish
   the named-character world. They probably belong before teaching stories so the
   narrative world exists before concept-grounding stories reference it. Untested.
3. **Which triplet tiers go where?** Tier 1–2 interleave with teaching story early
   passes. Tier 3–4 follow after the semantic substrate is more stable.

---

## Success criteria

A curriculum ordering is successful if it produces a checkpoint where:

- **B/D/E concepts absorbed** — confirmed by competency probes, not just shaped score
- **Cluster coherence** — brain_map after-hub μ shows tight intra-category similarity
  for emotion, cognitive, abstract (target: approaching Phase A level, ~0.85+)
- **Boolean discrimination works** — yes/no correct across all 4 languages
- **Dative stability** — consistent case form across rephrasings (intra-cluster
  after-hub improves from C13 baseline)
- **Arithmetic robustness** — correct across ≥ 3 surface rephrasings
- **Multilingual integrity** — DE/JP/ZH maintain register and script; ZH/EN near-parity;
  JP gap closes from current ~0.02 below EN
- **Shaped score stable** — sustained across ≥ 3 probe rounds (regression gate only,
  not primary success criterion)

---

## How to use this document for deep research

1. Feed this document together with `docs/brain_map.md` and brain-map results
   (`tmp/brain_map_hubs.json` or named scan outputs) to a deep research tool.
2. Ask it to:
   - Given the confirmed vignettes breakthrough and EDJC rotation finding, propose
     whether vignettes should move earlier in the block sequence
   - Identify whether the reasoning-format regression (E1 drop from 0.946→0.828)
     is addressable by interleaving reasoning with a larger corpus vs. standalone pass
   - Propose what the competency probe battery should look like at the bridge
     checkpoint specifically (after grammar, before teaching stories)
   - Identify whether JP fragility (consistently weakest language in all blocks)
     suggests a JP-first rotation variant or a JP-specific repair block
3. Cross-reference proposals against the corrected bridge interpretation.
4. Test divergences as controlled experiments.

---

## Related docs

- `training/pipeline/training.md` — active MSM session training procedure
- `docs/brain_map.md` — activation atlas methodology and v2 probe design
- `docs/boolean_stories.md` — boolean teaching story spec
- `training/logs/campaign_14_reports/` — C14a, C14b, C14c campaign reports
- `training/logs/campaign_15_reports/` — C15 reports (complete)
- `todo.md` — active work queue and campaign status
