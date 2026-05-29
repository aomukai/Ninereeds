# run_10 — Counting curriculum + full corpus

## Setup

| Field | Value |
|---|---|
| Run name | run_10_counting |
| Base checkpoint | checkpoints/run7_e1.pt (shaped 0.924 — cleanest baseline) |
| Corpus | training/corpus/run10_corpus.txt (13.54 MB, 24,937 files) |
| New content | 36 counting files (02_counting_*.md) in reasoning/, sorted before addition_* |
| Epochs | 3 |
| LR | 1e-3 (cosine decay per epoch) |
| AMP | bf16 enabled |

## Motivation

Counting experiment (run_10 diagnostic, E1–E3 on counting corpus only) showed:
- Format transfer is instant (1 epoch) — model produces "X plus Y is [number]" immediately
- Fact anchoring does NOT happen in isolation — answers are wrong but numerically shaped
- Register bleed is severe when counting corpus runs alone

Conclusion: counting must run alongside the full corpus, not in isolation.

The 36 counting files teach:
- Ordinal chain 0→1→2→3→4→…→9999 via +1/+10/+100/+1000 increments
- Both word form ("Three plus one is four") and numeral form ("3+1=4")
- All four languages (EN/DE/JP/ZH), each reinforcing "four" without competing "two" bleed

The ordinal chain 3+1=4 directly grounds "four" as the successor of "three" — something
no previous intervention established. Combined with existing arithmetic drill files
(addition_1_digit_facts.md etc.), the counting chain should anchor the answer slot.

Base is run7_e1 (0.924) — same as run_9. run_8 and run_9 both regressed shaped score;
run7_e1 remains the cleanest base before any arithmetic intervention.

---

## Epoch 1

**Loss:** 0.6613 (47 min)
**Checkpoint:** `core/run_10_counting_e1.pt`

### Probe results
```
Arithmetic:   0/3 correct  (1+3=4✗  5+5=10✗  3+3=6✗)
              Format intact — "Three plus three is three" (number word, wrong answer)
Dative:       1/3 correct  (über der Stadt ✓; über dem Schloss → "über dem Schlag" wrong noun)
Base spatial: über dem Berg ✓ (recovered vs run7_e1 baseline — counting didn't hurt lang_4)
Zero probe:   "zero is a number. We write it with the symbol 13" — counting template, wrong content
Phase probes: clean (5-line descriptions, no register bleed from counting)
```

### Eval results
```
RAW:    0.913
SHAPED: 0.901  (delta −0.012 vs shaper)
Failures: loop 2×, abrupt_stop 1×
Worst: "Why do birds sing?" (0.63 shaped — shaper misfired to JP)
Note: E1 dip typical; baseline run7_e1 shaped was 0.924
```

---

## Epoch 2

**Loss:**
**Checkpoint:** `core/run_10_counting_e2.pt`

### Probe results
```

```

### Eval results
```

```

---

## Epoch 3

**Loss:**
**Checkpoint:** `core/run_10_counting_e3.pt`

### Probe results
```

```

### Eval results
```

```

---

## Summary

**This run is part of a three-way scaling study:**
- run_10 → 25M baseline (this run)
- run_11 → 150M same corpus, scratch (`--scale-150m`)
- run_12 → ~300M same corpus, scratch (config TBD — GPT-2 size)

Fixed variable: corpus + procedure. Varying: model size only.

**Arithmetic retention check:** Did any epoch produce correct answers across ≥2/3 random arithmetic probe pairs?

- [ ] Yes → promote best epoch to `checkpoints/run10_counting.pt`
- [ ] No  → document as 25M baseline; proceed to run_11 (150M)

**Selected checkpoint:**

**Key observations:**
