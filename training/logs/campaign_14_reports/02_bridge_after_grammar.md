# Campaign 14b — Bridge after grammar (ordering variant)

## Setup

| Field | Value |
|---|---|
| Campaign | 14b |
| Report | 02 — Bridge-after-grammar variant |
| Model | 25M (default — no scale flag) |
| Base checkpoint | `checkpoints/c13_Phase_C_winner.pt` (shaped 0.925) |
| Corpus | `training/corpus/campaign14b_full.txt` |
| Corpus size | 36.13 MB / 37,569 files |
| Order file | `training/corpus_admin/campaign14b_manifest.txt` |
| Curriculum order | phase_A → phase_B → lang_1/2 → grammar → lang_3/4/5 → **bridge** → teaching → boolean |
| Shuffle | DISABLED (`--no-shuffle`) — order is intentional |
| Optimizer | AdamW (bf16 AMP) |
| LR | 1e-3 (cosine decay) |
| Epochs | 3 (ordering comparison — extend if winner) |
| GPU | CUDA:0 (dedicated training card, RTX 3060 12GB) |
| Eval GPU | CUDA:1 (daily-use card, RTX 3060 12GB) |
| Compare against | `01_full_curriculum.md` (bridge before grammar) |

## Hypothesis

Bridge placed after grammar + lang_3/4/5 acts as corrective consolidation pressure on
already-learned case structure, rather than as a cold-start primer. The model first
internalises the grammar rules (modules 1–11), applies them in multilingual context
(lang_3/4/5), then gets a surface-form drill that targets its actual misconceptions
rather than pre-loading before any grammar exposure.

This mirrors the C13 finding: "Bridge as between-phase connector: -0.008 to -0.018
(consistently hurt)". In that case bridge was inserted mid-sequence; here it comes
after the full grammar block, which may change the dynamic.

## Launch command

```bash
CUDA_VISIBLE_DEVICES=0 nohup /home/aomukai/.unsloth/studio/unsloth_studio/bin/python train.py \
  --phase 0 \
  --corpus-file training/corpus/campaign14b_full.txt \
  --output core/campaign14b_full.pt \
  --resume checkpoints/c13_Phase_C_winner.pt \
  --epochs 3 \
  --epoch-checkpoints \
  --amp-bf16 \
  --no-shuffle \
  > training/logs/campaign_14_reports/02_bridge_after_grammar_train.log 2>&1 &
echo "PID: $!"
```

Monitor for first epoch:
```bash
until [ -f core/campaign14b_full_e1.pt ]; do sleep 60; done && echo "E1 ready"
```

---

## Per-epoch probe summary

| Epoch | FC pass | Garbled | Sentences | Pronouns | Arith | Dative | Notes |
|---|---|---|---|---|---|---|---|
| E1 | (fill) | (fill) | (fill) | (fill) | (fill) | (fill) | |
| E2 | (fill) | (fill) | (fill) | (fill) | (fill) | (fill) | |
| E3 | (fill) | (fill) | (fill) | (fill) | (fill) | (fill) | |

---

## Module status tracker

Same thresholds and block→category mapping as 01_full_curriculum.md.
Key comparison point: does grammar cluster (μ after hubs) converge faster here than in 14a?

### E1 module status (brain_map: c14b_e1_language)

Hubs: 3,332 (1.69%) — notably higher than A-E1 (2,208). Semantic neurons: grammar 519, multilingual 459, arithmetic 397.

| Block | Key categories | After-hub μ | Verdict | Consecutive DONE |
|---|---|---|---|---|
| phase_A | animals 0.684 / objects 0.736 / vehicles 0.778 | KEEP (all below 0.80) | 0 |
| phase_B | boundary 0.373 / movement 0.407 | **WEAK** (both) | — |
| lang_1/2 | multilingual 0.246 | **WEAK** | — |
| grammar+lang_3/4/5+bridge | grammar 0.277 / spatial 0.154 | **WEAK** (both) | — |
| teaching stories | emotions 0.764 / cognitive 0.600 / abstract 0.515 / time 0.219 | KEEP (emotions, cognitive, abstract) · WEAK (time) | — |
| boolean stories | animals_boolean 0.509 / emotions_boolean 0.864 | WEAK (animals_bool) · **DONE** ×1 (emotions_bool) | 1 for emotions_bool |

**vs A-E1:** grammar 0.277 vs A's 0.284 (marginally worse). Phase_A concrete concepts also lower (vehicles 0.778 vs A's 0.937). Bridge-after appears to delay both grammar and concrete cluster formation at E1.

### E2 module status (brain_map: c14b_e2_language)

Hubs: 3,160 (1.61%) — declining (good), but still well above A-E1's 2,208. Semantic neurons: grammar 462, multilingual 446, arithmetic 380.

| Block | Key categories | After-hub μ | Verdict | Consecutive DONE |
|---|---|---|---|---|
| phase_A | animals 0.866 / objects 0.937 / vehicles 0.959 | **DONE** ×1 (all three) | 1 |
| phase_B | boundary 0.511 / movement 0.360 | KEEP (boundary) · **WEAK** (movement) | — |
| lang_1/2 | multilingual 0.242 | **WEAK** | — |
| grammar+lang_3/4/5+bridge | grammar 0.209 / spatial 0.138 | **WEAK** (both) | — |
| teaching stories | emotions 0.425 / cognitive 0.702 / abstract 0.412 / time 0.315 | KEEP (cognitive) · **WEAK** (rest) | — |
| boolean stories | animals_boolean 0.631 / emotions_boolean 0.608 | KEEP (both) — emotions_bool dropped from DONE | 0 |

**vs A-E2:** grammar 0.209 vs A's 0.243 — bridge-after is definitively worse for grammar cluster. Concrete concepts strongly better: vehicles 0.959 vs A's ~0.850, objects 0.937. emotions_boolean dropped from DONE (0.864→0.608) — instability; the boolean block appears to consolidate later in B ordering.

### E3 module status (brain_map: c14b_e3_language)

Hubs: 4,106 (2.09%) — **increasing** from E2's 3,160. Semantic neurons: arithmetic 919, grammar 723, time 593, multilingual 459, spatial 319. Total semantic neurons: 4,094 (vs 2,463 at E2) — model still allocating dedicated circuits heavily.

| Block | Key categories | After-hub μ | Verdict | Consecutive DONE |
|---|---|---|---|---|
| phase_A | animals 0.710 / objects 0.752 / vehicles 0.784 | KEEP — all dropped sharply from E2 peaks | 0 |
| phase_B | boundary 0.376 / movement 0.424 | **WEAK** (both) | — |
| lang_1/2 | multilingual 0.268 | **WEAK** | — |
| grammar+lang_3/4/5+bridge | grammar 0.205 / spatial 0.280 | **WEAK** (both) | — |
| teaching stories | emotions 0.487 / cognitive **0.840** / abstract 0.399 / time 0.349 | **DONE** ×1 (cognitive) · KEEP (emotions, abstract) · WEAK (time) | 1 for cognitive |
| boolean stories | animals_boolean 0.434 / emotions_boolean 0.751 | **WEAK** (animals_bool) · KEEP (emotions_bool) | 0 |

**Notable:** concrete clusters peaked sharply at E2 then regressed at E3 (vehicles 0.959→0.784, objects 0.937→0.752) — instability not seen in A. Hub count rising at E3 is a warning sign. Cognitive hit DONE ×1 (0.840), better than A's E3 (0.685).

---

## Probe results per epoch

### E1

```
(paste probe.py output)
```

brain_map cluster notes:
- grammar dative/accusative: (fill — key comparison point vs 14a)
- multilingual EN/DE/JP/ZH: (fill)
- emotions/movement/abstract: (fill)

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

---

## Comparison vs 14a (bridge before grammar)

After-hub μ comparison across all three epochs:

| Metric | A-E1 | A-E2 | A-E3 | B-E1 | B-E2 | B-E3 | Better |
|---|---|---|---|---|---|---|---|
| grammar μ | 0.284 | 0.243 | 0.201 | 0.277 | 0.209 | 0.205 | **A** (consistently higher) |
| multilingual μ | 0.216 | — | 0.204 | 0.246 | 0.242 | 0.268 | **B** (slowly improving; A flat) |
| vehicles μ | 0.937 | — | 0.879 | 0.778 | 0.959 | 0.784 | **A** (more stable; B volatile) |
| objects μ | 0.873 | — | 0.856 | 0.736 | 0.937 | 0.752 | **A** (stable); B peaks then falls |
| animals μ | 0.879 | — | 0.740 | 0.684 | 0.866 | 0.710 | **A** (A declining too; roughly tied) |
| cognitive μ | 0.596 | — | 0.685 | 0.600 | 0.702 | **0.840** | **B** (clear winner) |
| emotions μ | 0.551 | — | 0.283 | 0.764 | 0.425 | 0.487 | **B** (higher throughout) |
| emotions_boolean μ | 0.871 | — | 0.820 | 0.864 | 0.608 | 0.751 | **A** (more stable) |
| Hub count E1→E3 | 2,208→? | | | 3,332→4,106 | | | **A** (B hubs rising at E3) |
| Semantic neurons E3 | 3,825 | | | 4,094 | | | B allocating more |

**Winner: A (bridge before grammar)**

**Reason:** Grammar cluster is the primary target for this campaign — bridge-before ordering consistently produces higher grammar μ at all three epochs (0.284/0.243/0.201 vs 0.277/0.209/0.205). The concrete concept clusters (vehicles, objects) are more stable in A; B shows high peaks at E2 but sharp regression at E3, suggesting hub interference from the late grammar+bridge block. B's rising hub count at E3 (4,106 vs E2's 3,160) confirms the model is consolidating into shared routing rather than building clean separate clusters.

B does win for cognitive (0.840 vs 0.685) and emotions (0.487 vs 0.283) — the bridge coming after lang_3/4/5 may give teaching stories a better-prepared substrate. Worth noting but not enough to override grammar.

**Next step:** campaign14c focused corpus using A ordering (bridge before grammar). Drop phase_A vehicle + object files (A: DONE ×3). Expand bridge per `docs/bridge_expansion_design.md` before running.

---

## Best checkpoint

| Field | Value |
|---|---|
| Selected epoch | (fill) |
| Checkpoint path | `core/campaign14b_full_eN.pt` |
| Saved to | `checkpoints/c14b_winner.pt` (if winner over 14a) |

---

## Eval commands (run after each checkpoint on CUDA:0 or any free GPU)

```bash
CKPT=core/campaign14b_full_eK.pt   # substitute K
PYTHON=/home/aomukai/.unsloth/studio/unsloth_studio/bin/python

CUDA_VISIBLE_DEVICES=1 $PYTHON meta/scripts/probe.py \
  --checkpoint "$CKPT" --temperature 0.7 --tokens 120

CUDA_VISIBLE_DEVICES=1 $PYTHON eval.py --checkpoint "$CKPT"

CUDA_VISIBLE_DEVICES=1 $PYTHON meta/scripts/brain_map.py probe \
  --checkpoint "$CKPT" \
  --probes training/corpus_admin/probe_sets/language.jsonl \
  --name c14b_eK_language

CUDA_VISIBLE_DEVICES=1 $PYTHON meta/scripts/brain_map.py map --name c14b_eK_language
CUDA_VISIBLE_DEVICES=1 $PYTHON meta/scripts/brain_map.py hubs --name c14b_eK_language --threshold 0.7
```
