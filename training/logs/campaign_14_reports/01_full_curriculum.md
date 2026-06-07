# Campaign 14 — Full Language Curriculum

## Setup

| Field | Value |
|---|---|
| Campaign | 14 |
| Report | 01 — Full language curriculum |
| Model | 25M (default — no scale flag) |
| Base checkpoint | `checkpoints/c13_Phase_C_winner.pt` (shaped 0.925) |
| Corpus | `training/corpus/campaign14_full.txt` |
| Corpus size | 36.13 MB / 37,569 files |
| Order file | `training/corpus_admin/campaign14_manifest.txt` |
| Curriculum order | phase_A → phase_B → lang_1/2 → bridge → grammar → lang_3/4/5 → teaching+triplets → boolean |
| Shuffle | DISABLED (`--no-shuffle`) — order is intentional |
| Optimizer | AdamW (bf16 AMP) |
| LR | 1e-3 (cosine decay) |
| Epochs | 3 (ordering comparison vs 14b — extend to 5 if winner) |
| GPU | CUDA:0 (dedicated training card, RTX 3060 12GB) |
| Eval GPU | CUDA:1 (daily-use card, RTX 3060 12GB) |

## Motivation

Campaign 13 reached a ceiling of 0.925 shaped on concrete anchors + agents/social (phases A+C).
Phases B/D/E (emotion, cognitive, abstract) permanently failed in static-property format — the leading
hypothesis is lack of narrative grounding.

Campaign 14 addresses this by:
1. Establishing the full language curriculum (grammar, multilingual, spatial, Q&A) as a foundation
2. Delivering 5006 teaching stories grounded in emotion/movement/cognition/abstraction domains
3. Adding 800 boolean stories for observable-state discrimination
4. Interleaving with 1345×4 triplet stories, domain-aligned

Primary goal: language cluster tightening (multilingual coherence, JP/ZH μ ≥ 0.85/0.80) and
first emergence of emotion/movement/cognitive/abstract clusters in brain_map.

Eval method: probe + brain_map (language probe set) after every epoch. No loss curves, no fixed epoch count.
Stop criterion: per-module after-hub μ — see Module Status tracker below.

---

## Launch command

```bash
CUDA_VISIBLE_DEVICES=0 nohup /home/aomukai/.unsloth/studio/unsloth_studio/bin/python train.py \
  --phase 0 \
  --corpus-file training/corpus/campaign14_full.txt \
  --output core/campaign14_full.pt \
  --resume checkpoints/c13_Phase_C_winner.pt \
  --epochs 3 \
  --epoch-checkpoints \
  --amp-bf16 \
  --no-shuffle \
  > training/logs/campaign_14_reports/01_full_curriculum_train.log 2>&1 &
echo "PID: $!"
```

Monitor for first epoch:
```bash
until [ -f core/campaign14_full_e1.pt ]; do sleep 60; done && echo "E1 ready"
```

---

## Per-epoch probe summary

| Epoch | FC pass | Garbled | Sentences | Pronouns | Arith | Dative | Notes |
|---|---|---|---|---|---|---|---|
| E1 | 1/8 | 1/17 | 3/17 | 1/17 | 0/3 | 0/3 | Warmup noise; boolean format bleeding into all probes |
| E2 | (fill) | (fill) | (fill) | (fill) | (fill) | (fill) | |
| E3 | (fill) | (fill) | (fill) | (fill) | (fill) | (fill) | |

---

## Module status tracker

**Thresholds** (after-hub cosine similarity μ, from `brain_map.py hubs`):

| Verdict | After-hub μ | Meaning |
|---|---|---|
| **DONE** | ≥ 0.80 | Tight cluster, stable — drop block from next run |
| **KEEP** | 0.60–0.79 | Forming — retain, watch next epoch |
| **WEAK** | < 0.60 | Minimal structure — prioritise in next run |

Rule: mark a block DONE only after it holds ≥ 0.80 for **2 consecutive epochs**. Single-epoch spikes can be noise.

**Block → brain_map category mapping:**

| Block | Brain_map categories |
|---|---|
| phase_A | animals, objects, vehicles |
| phase_B | boundary, movement |
| lang_1/2 | multilingual |
| bridge + grammar + lang_3/4/5 | grammar, spatial |
| teaching stories | emotions, emotions_boolean, emotions_boundary, cognitive, abstract, time, movement |
| boolean stories | animals_boolean, emotions_boolean, boundary |

---

### E1 module status (brain_map: c14_e1_language)

| Block | Key categories | After-hub μ | Verdict | Consecutive DONE |
|---|---|---|---|---|
| phase_A | animals / objects / vehicles | 0.879 / 0.873 / 0.937 | **DONE** (animals/objects/vehicles) | 1 |
| phase_B | boundary / movement | 0.652 / 0.414 | KEEP (boundary) · WEAK (movement) | — |
| lang_1/2 | multilingual | 0.216 | **WEAK** | — |
| bridge+grammar+lang_3/4/5 | grammar / spatial | 0.284 / 0.151 | **WEAK** | — |
| teaching stories | emotions / cognitive / abstract / time | 0.551 / 0.596 / 0.411 / 0.261 | KEEP (emotions, cognitive) · WEAK (abstract, time) | — |
| boolean stories | animals_boolean / emotions_boolean | 0.694 / 0.871 | KEEP (animals_bool) · DONE (emotions_bool) | 1 |

**Notable:** grammar has 513 dedicated semantic neurons — most of any category — but μ=0.284. Knowledge is encoded but not yet consolidated into a tight cluster.

**Next run (tentative, pending E2):** keep all blocks. If phase_A categories hold ≥ 0.80 at E2, drop phase_A block from E3 run.

---

### E2 module status

| Block | Key categories | After-hub μ | Verdict | Consecutive DONE |
|---|---|---|---|---|
| phase_A | animals / objects / vehicles | (fill) | (fill) | (fill) |
| phase_B | boundary / movement | (fill) | (fill) | — |
| lang_1/2 | multilingual | (fill) | (fill) | — |
| bridge+grammar+lang_3/4/5 | grammar / spatial | (fill) | (fill) | — |
| teaching stories | emotions / cognitive / abstract / time | (fill) | (fill) | — |
| boolean stories | animals_boolean / emotions_boolean | (fill) | (fill) | (fill) |

**Next run manifest:** (fill after E2 — list blocks to keep/drop)

---

### E3 module status

| Block | Key categories | After-hub μ | Verdict | Consecutive DONE |
|---|---|---|---|---|
| phase_A | animals 0.740 / objects 0.856 / vehicles 0.879 | mixed | objects+vehicles **DONE ×3**; animals KEEP (declining) | 3 for vehicles+objects |
| phase_B | boundary 0.512 / movement 0.361 | WEAK | both declining | — |
| lang_1/2 | multilingual 0.204 | WEAK | flat | — |
| bridge+grammar+lang_3/4/5 | grammar 0.201 / spatial 0.208 | WEAK | grammar declining all 3 epochs; 531 dedicated neurons | — |
| teaching stories | emotions 0.283 / cognitive 0.685 / abstract 0.213 / time 0.229 | mixed | cognitive KEEP; rest WEAK | — |
| boolean stories | animals_boolean 0.531 / emotions_boolean 0.820 | mixed | emotions_boolean DONE ×1 (dipped E2); animals_boolean WEAK | 1 for emotions_bool |

**Notable:** arithmetic has 1,296 dedicated semantic neurons (most of any category, up from 343 at E2) — knowledge encoding without cluster formation. Grammar has 531. Both show the model is allocating dedicated capacity but not consolidating.

**Next run:** variant B (bridge after grammar) is now running for comparison. After B's E3, build focused corpus:
- DROP from phase_A: all vehicle files + all object files
- DROP if emotions_boolean holds ≥ 0.80 at B-E1: boolean_stories block (or thin to animals_boolean only)
- KEEP everything else — especially grammar block which needs the most work

---

## Probe results per epoch

### E1

```
(paste probe.py output)
```

brain_map cluster notes:
- animals/mammals: (fill)
- multilingual EN/DE: (fill)
- multilingual JP/ZH: (fill)
- grammar dative/accusative: (fill)
- arithmetic: (fill)
- emotions: (fill — new cluster target)
- movement: (fill — new cluster target)
- abstract_properties: (fill — new cluster target)

### E2

```
(paste probe.py output)
```

brain_map cluster notes:
- (fill)

### E3

```
(paste probe.py output)
```

brain_map cluster notes:
- (fill)

### E4

```
(paste probe.py output)
```

brain_map cluster notes:
- (fill)

### E5

```
(paste probe.py output)
```

brain_map cluster notes:
- (fill)

---

## Best checkpoint

| Field | Value |
|---|---|
| Selected epoch | (fill) |
| Reason | (fill) |
| Checkpoint path | `core/campaign14_full_eN.pt` |
| Saved to | `checkpoints/c14_winner.pt` |

Promotion command:
```bash
BEST_EPOCH=eN   # fill in
cp core/campaign14_full_${BEST_EPOCH}.pt checkpoints/c14_winner.pt
ls -lh checkpoints/c14_winner.pt
find core/ -name "campaign14_full_e*.pt" ! -name "campaign14_full_${BEST_EPOCH}.pt" -delete
ls core/campaign14_full*.pt
```

---

## Key observations

(fill after all epochs complete)

- Did shaped score hold above 0.925 base?
- Did JP/ZH multilingual μ improve toward targets (≥ 0.85 / ≥ 0.80)?
- Did emotion/movement/abstract clusters emerge at all?
- Did grammar cluster survive (dative μ 0.45–0.55, accusative ≥ 0.90)?
- Any new failure modes (loops, garbling, tag bleed)?

---

## Eval commands (run after each checkpoint on CUDA:1)

```bash
CKPT=core/campaign14_full_eK.pt   # substitute K
PYTHON=/home/aomukai/.unsloth/studio/unsloth_studio/bin/python

CUDA_VISIBLE_DEVICES=1 $PYTHON meta/scripts/probe.py \
  --checkpoint "$CKPT" --temperature 0.7 --tokens 120

CUDA_VISIBLE_DEVICES=1 $PYTHON eval.py --checkpoint "$CKPT"

CUDA_VISIBLE_DEVICES=1 $PYTHON meta/scripts/brain_map.py probe \
  --checkpoint "$CKPT" \
  --probes training/corpus_admin/probe_sets/language.jsonl \
  --name c14_eK_language

CUDA_VISIBLE_DEVICES=1 $PYTHON meta/scripts/brain_map.py map --name c14_eK_language
CUDA_VISIBLE_DEVICES=1 $PYTHON meta/scripts/brain_map.py hubs --name c14_eK_language --threshold 0.7
```
