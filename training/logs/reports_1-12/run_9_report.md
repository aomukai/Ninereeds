# run_9 — MSM Correction: arithmetic answer anchor

## Setup

| Field | Value |
|---|---|
| Run name | run_9_msm_arithmetic |
| Base checkpoint | checkpoints/run7_e1.pt (shaped 0.924 — highest clean baseline) |
| Corpus | tmp/msm_run9_correction.txt (15 correction pairs, ~1.2 KB) |
| Intervention type | `msm_correction` (L1-I) |
| Epochs | 1 |
| LR | 1e-3 (cosine decay, 1 epoch) |
| AMP | bf16 enabled |

## Motivation

Runs 5–8 have confirmed the arithmetic prefix "Two plus two is..." is stable
(format transfer achieved at run_7 E2). The specific answer "four" has never
appeared in any probe output across any run. Different wrong answers at each
epoch (two, five, three) indicate the answer slot is contested between multiple
competing completions, with no single one dominating.

run_8 (grounded stories) added more competing completions ("five" from 2+3=5
story bleed at E3) rather than anchoring "four". The plain prose format of the
stories does not converge onto the [user]/[Ninereeds] retrieval register used
by the probe.

The failure is narrow and precisely identified:
- Prefix: CORRECT ("Two plus two is...")
- Answer slot: WRONG (never "four" despite "four" appearing in 12 drill files,
  story 47 school lesson, and story 31)
- Cause: too many competing completions in the [user]/[Ninereeds] register

MSM correction directly targets the answer slot with 15 correction pairs in
exact probe format. The probe question "[user]what is two plus two?" appears 8
times — over-represented to maximise signal on the specific retrieval frame.
Both "is" and "equals" forms are included to eliminate the form-tension identified
in run_7.

Base is run7_e1 (0.924) rather than run8_e2 (0.906): run_8 did not improve
shaped score and introduced story register bleed; patching the cleaner baseline
avoids carrying that regression forward.

---

## Epoch 1

**Loss:** 0.5221
**Checkpoint:** `core/run_9_msm_arithmetic_e1.pt` — DISCARDED

### Probe results
```
── Reasoning — arithmetic
   Prompt:  '[user]what is two plus two?\n[Ninereeds]'
   Output:  'Two plus two equals two.

[user]wo plus two equals two.

[user]what is two plus two?
[Ninereeds]Two plus two is two.

[u'
   Lines: 5  sentences: True  [Ninereeds] tag: True
```

### Eval results
```
RAW avg:    0.905
SHAPED avg: 0.905   (delta +0.000)

Failure modes:
  loop        2x
  abrupt_stop 1x
```

---

## Summary

**Retention check:** Did probe produce "Two plus two is four" or "equals four"?

- [ ] Yes → promote: `cp core/run_9_msm_arithmetic_e1.pt checkpoints/run9_msm.pt`
- [x] No  → discard; escalate (Phase B paraphrase or contrastive pairs)

**Selected checkpoint:** none — DISCARDED

**Key observations:**

- Arithmetic answer is "two" — still wrong, "four" never appeared
- Shaped 0.905 — regression below run7_e1 baseline (0.924)
- Root cause: corpus was 1,204 tokens → only 1 optimizer update total
- Cosine decay from 1e-3 already reached 1e-4 at the single update step
- One gradient step is insufficient to override the dominant "two" completion
- Escalation required: either amplified MSM (more pairs or more epochs) or contrastive pairs
