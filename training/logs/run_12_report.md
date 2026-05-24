# run_12 — Scaling study 604M (1 epoch)

## Setup

| Field | Value |
|---|---|
| Run name | run_12_600m |
| Base checkpoint | scratch (no resume — fresh initialisation) |
| Corpus | training/corpus/run10_corpus.txt (13.54 MB, 24,937 files) |
| Epochs | 1 |
| LR | 1e-3 (cosine decay) |
| AMP | bf16 enabled |
| Batch size | 2 (batch_size=2 OOM with standard AdamW; fixed with AdamW8bit) |
| Optimizer | AdamW8bit (bitsandbytes 0.49.2) — optimizer states in 8-bit, saves ~4 GB vs fp32 AdamW |
| Model | XL_600M_CONFIG — n_layer=6, n_embd=512, n_head=8, per_layer_weights=True (604.2M actual) |

## Motivation

Part 3 of the two-step ablation: depth fixed at n_layer=6, width scaled from 256→512.

| Run | Params | What changes |
|---|---|---|
| run_10 | 25.3M | baseline — shared layer weights |
| run_11 | 151.1M | per_layer_weights=True (same 256-dim) — layer independence added |
| run_12 | 604.2M | n_embd=512 (same depth, same per_layer_weights) — wider internal space |

run_11 showed: format learned, answer slot echoes question word ("two plus two is **two**"). Per_layer_weights alone did not anchor arithmetic facts. Hypothesis for run_12: wider embedding (512 vs 256) provides enough associative separation in the hidden state that the answer slot can bind to the correct numeral rather than repeating the question context.

Note: RNG fix applied before run_12 (isolated data-order Generator, seed=1337+epoch). Data order is now controlled and identical to run_10/11 per-epoch, independent of model init RNG.

---

## Epoch 1

**Loss:** 1.1004  (9878.8s, ~2.7 hours)
**Checkpoint:** `core/run_12_600m_e1.pt`
**VRAM peak (batch_size=2):** 8.6 GB reserved (AdamW8bit; stable from step 25 onward)

### Probe results
```
============================================================
  Fixed comparison probes (cross-run reproducible)
============================================================
── FC — 1+1=2  → FAIL (want 'two')
   Prompt:  '[user]what is one plus one?\n[Ninereeds]'
   Output:  "One plus one is another person. one one plant of one's story is when they eat and it with a high real word. They have th"

── FC — 2+2=4  → FAIL (want 'four')
   Prompt:  '[user]what is two plus two?\n[Ninereeds]'
   Output:  'Two plus two is two plus two and two equals two through throwing and boundary through instruction. The two body was thro'

── FC — 3+1=4  → FAIL (want 'four')
   Prompt:  '[user]what is three plus one?\n[Ninereeds]'
   Output:  'Three plus one is three plus two plures two three hundred.\nTwo plus three is two hurter three three drink on two three t'

── FC — zero  → FAIL (want 'number')
   Prompt:  '[user]what is zero?\n[Ninereeds]'
   Output:  'Zero is a flat power with both sides.\nZero can be on a shoe.\nZero can be on a page.\nZero can be on a table.\nZero can be'

── FC — dative über  → FAIL (want 'dem')
   Prompt:  'Die Wolke ist über'
   Output:  'den Tisch.\nそのゴムは紙の前である。\n这个那个地图很大。\n\nThat load is carpented to the talk.\nDieser'

── FC — acc movement  → FAIL (want 'den')
   Prompt:  'Das Kind geht in'
   Output:  'der Bärender halten Materialen. Sie legte einen Holzstuhl gelernte seinen Kühlen, seinen Floppstoff hinterließ. Der'

── FC — JP autumn  → FAIL (want '秋')
   Prompt:  '[user]秋について話してください。\n[Ninereeds]'
   Output:  'アビリは大きな木の後、事実の料理について歩いた。表面の隙間がありまさに薄く見てい'

── FC — ZH autumn  → FAIL (want '秋')
   Prompt:  '[user]告诉我关于秋天的故事。\n[Ninereeds]'
   Output:  '身体放在教室餐廳走路旁，因為如果他們的洞裡有道路來的設計。他正在把書館的每個孩子'

   Fixed comparison: 0/8 pass

============================================================
  Format probes
============================================================
   Lines: avg 4-5  sentences: 16/17  [Ninereeds] tag: present
   Garbled output: 1/17 (JP autumn — no sentence breaks)
   Pronoun use: 0/17
   Negation use: 0/17

============================================================
  Randomised arithmetic probes
============================================================
── Arithmetic — 1+3=4  → WRONG  Output: 'One plus two is belong to be three...'
── Arithmetic — 4+1=5  → WRONG  Output: 'Four plus one is four.'
── Arithmetic — 1+1=2  → WRONG  Output: 'One plus one is plus one.'
   Arithmetic: 0/3 correct

============================================================
  Randomised dative probes (über + location noun)
============================================================
── Dative — über dem Hügel (m)  → MISSING   Output: 'im Hilfe.'
── Dative — über der Straße (f) → MISSING   Output: 'vor der Frau.'
── Dative — über dem Dorf (n)   → MISSING   Output: 'auf dem Bild.'
   Dative: 0/3 correct
```

### Eval results
```
============================================================
  RAW avg:    0.913
  SHAPED avg: 0.915   (delta +0.002)
============================================================

  Failure modes detected:
    loop                  1x

  Worst shaped outputs:
  [0.78] 'I am hungry because '
  [0.82] 'A book is'  (loop detected)
  [0.83] 'The reason I like reading is '

  Best shaped outputs:
  [0.98] 'It was a dark and quiet night when'
  [0.98] 'Q: How does a rainbow form?\nA:'
  [0.96] 'Q: Why do we sleep?\nA:'
```

---

## Summary

**Scaling study comparison (1 epoch each):**

| Run | Size | Base | Loss E1 | RAW E1 | Shaped E1 | Loops | Arith E1 | Dative E1 | FC E1 |
|---|---|---|---|---|---|---|---|---|---|
| run_10 | 25.3M | run7_e1 | 0.6613 | 0.913 | 0.901 | 2 | 0/3 | 1/3 | — |
| run_11 | 151.1M | scratch | 1.1016 | 0.873 | 0.913 | 2 | 0/3 | 0/3 | 1/8 |
| run_12 | 604.2M | scratch | 1.1004 | 0.913 | 0.915 | 1 | 0/3 | 0/3 | 0/8 |

**Arithmetic improvement check:**

- [x] No  → arithmetic fails at all three scales — curriculum/architecture problem, not capacity

Width increase (151M→604M) improved RAW and reduced loops but did NOT break echo pressure at 1 epoch. FC dropped from 1/8 to 0/8 — more parameters from scratch with 1 epoch does not recover the sparse fixed-comparison signals that run_11 barely caught.

**Selected checkpoint:** none — not promoted. Scaling study baseline only.

**Key observations:**

1. **Echo pressure is not a capacity failure.** "Two plus two is two plus two and two equals two through throwing" — the answer slot is still dominated by recency/repetition at 604M. Width alone does not separate the answer token from question context at 1 epoch from scratch.

2. **FC regression from 11→12.** run_11 got 1/8 (dative "über dem Berg" partial); run_12 gets 0/8. Larger model starting from scratch needs more epochs to recover signal density. The FC table now serves as a clean cross-run anchor.

3. **Format quality is clean.** Phase format holds at 604M: 0 pronouns, 0 negations, 16/17 with sentences, 1 garbled (JP autumn). The format discipline from curriculum persists at wider scale.

4. **Loops improve with scale.** 25M: 2 loops, 151M: 2 loops, 604M: 1 loop. Wider hidden state reduces degenerate repetition even at 1 epoch — consistent with more representational headroom, not better fact binding.

5. **Scaling study verdict.** Same corpus, same depth (6 layers), 1 epoch from scratch: arithmetic 0/3 at 25M / 151M / 604M. Problem is not parameter count — it is curriculum ordering and cluster structure. The dative probe also 0/3 at all three scales for the first time; run_10 had 1/3 from the run7 checkpoint (prior training), run_11 and run_12 start from scratch and get none.

6. **Next lever: curriculum cluster ordering.** Grammar-function-first sequencing (dative cluster → accusative cluster → math cluster) is the intervention to test before any further scaling. Max out 150M with targeted curriculum before committing 604M cycles.
