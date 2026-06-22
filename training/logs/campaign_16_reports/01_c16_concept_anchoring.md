# Campaign 16 — Block 1: Concept Anchoring

**Date:** 2026-06-22  
**Base:** fresh init (no prior checkpoint)  
**Corpus:** `training/corpus/redesign_c16.txt` — 34,645 files (33,966 concept + 679 identity insertions)  
**Probe set:** `training/corpus_admin/probe_sets/c16_concepts.jsonl` — 60 probes, 10 categories  
**Model:** small-25m (25.3M params)  
**Flags:** `--phase 0 --no-shuffle --batch-size 4 --epochs 1` per epoch  

---

## Motivation

C13–C15 trained a multilingual corpus (EN/DE/JP/ZH) and peaked at E2–E3. C16 hypothesis: the small model's capacity is being consumed by multilingual surface disambiguation before it can form semantic concept clusters. Strip to EN-only, semantic bucket ordering, identity interleaved every 50 files, multiple angles per word. Find the correct training recipe before adding complexity.

---

## Results

| Epoch | Shaped | Flags | Chat (12q) | Winner |
|---|---|---|---|---|
| E1 | 0.995 | 2 | —* | |
| E2 | 1.000 | 0 | "I am Ninereeds."* | |
| E3 | 0.998 | 3 | 5/12 | |
| **E4** | **0.996** | **0** | **9/12** | **★** |
| E5 | 0.995 | 1 | 8/12 | |

*E1/E2 chat tests ran with a broken method call; manually tested.  
E5 triggered STOP: 2/3 signals regressed simultaneously (shaped −0.001, flags +1, chat −1/12). All margins were tiny but the rule is 2/3.

**Winner: `core/c16_redesign_e4.pt`**

---

## Brain scan — hub structure

| Epoch | Routing hubs | Semantic neurons | Silent |
|---|---|---|---|
| E1 | 7.95% | 3.84% | 80.81% |
| E2 | 4.08% | 3.68% | 85.69% |
| E3 | 3.54% | 4.45% | 85.08% |
| E4 | 3.60% | 4.60% | 83.74% |
| E5 | 3.33% | 4.58% | 84.50% |

Routing hubs halved E1→E2 (7.95%→4.08%) as the model pruned general-purpose routers. Semantic neurons grew from 3.84% to 4.60% by E4 — more neurons becoming category-specific. Stabilised by E3.

---

## Brain scan — after-hub scores (intra-category similarity after hub removal)

| Category | E1 | E2 | E3 | E4 ★ | E5 |
|---|---|---|---|---|---|
| boundary | 0.435 | 0.366 | 0.391 | 0.409 | 0.455 |
| household | 0.214 | 0.328 | 0.439 | **0.542** | 0.381 |
| animals | 0.096 | 0.141 | 0.181 | **0.272** | 0.181 |
| colors | 0.157 | 0.210 | 0.190 | 0.220 | 0.231 |
| identity | 0.114 | 0.110 | 0.158 | 0.141 | 0.150 |
| nature | 0.054 | 0.084 | 0.103 | 0.104 | 0.083 |
| body | 0.153 | 0.122 | 0.158 | 0.158 | 0.127 |
| emotions | 0.125 | 0.228 | 0.133 | 0.064 | 0.059 |
| actions | 0.138 | 0.163 | 0.109 | 0.051 | 0.052 |
| food | 0.186 | 0.128 | 0.120 | 0.078 | 0.034 |

Brain map files: `training/logs/brain_maps/c16_eN_concepts_hubs.json` (N=1–5)

---

## Key observations

**1. Boundary is the most robustly learned concept.**  
The "I don't know" refusal pattern consistently has the highest after-hub score (0.37–0.46). It activates a stable, distinct cluster across all epochs. This is the first concept to genuinely crystallise.

**2. Concrete objects win over abstract categories.**  
Household (0.542) and animals (0.272) are the strongest semantic clusters in E4. Emotions, actions, and food decline in later epochs — their co-firing patterns are not yet distinct enough to hold against the training signal. Hebbian learning favours things with clearly distinct physical properties.

**3. Identity is behaviourally solid but structurally weak.**  
The model produces "I am Ninereeds." reliably (E2+), but the identity after-hub score is only 0.11–0.16. Identity responses are largely routed through general-purpose hubs rather than genuinely represented neurons. This makes identity fragile under further training — it needs reinforcement.

**4. Sustained learning past E2/E3 — recipe confirmed.**  
Prior campaigns (C13–C15, multilingual) peaked at E2–E3. C16 was still learning at E4. The combination of EN-only, semantic bucket ordering, identity interleaving every 50 files, and multiple question angles per word is the correct recipe for this model size.

**5. Chat quality trajectory.**  
E1: complete word salad ("resuddening", "wubcrigg"). E2: "I am Ninereeds." E3: topic words appear as sentence subjects ("An alligator has…", "Birds live…"). E4: 9/12 on-topic, correct boundary refusals, real vocabulary beginning to appear.

---

## Winner selection

E4 chosen over E5. E5 showed simultaneous regression on all three automated signals (shaped, flags, chat) by tiny margins. The trained eval signals align with manual chat impression: E4 is more coherent than E5.

Promote: `cp core/c16_redesign_e4.pt checkpoints/c16_concept_anchoring_winner.pt`

---

## Next block

C17 — Question rephrasing (`angle_aug.py --wave 1`): same concept facts, varied question surface forms. Goal: break the surface-form lock on abstract categories (emotions, actions, food) and strengthen identity representation. Build on E4 winner as base.

Signal to watch: do emotions/actions/food after-hub scores recover? Does identity after-hub cross 0.25?
