---
name: feedback-eval-philosophy
description: Eval priority order: brain_map first, shaped score second, raw third, loss dead last. Brain scan is mandatory before winner selection.
metadata:
  type: feedback
---

Evaluation priority order (highest to lowest):
1. **brain_map** — cluster structure, hub μ per category (language.jsonl + thinking.jsonl)
2. **shaped score** (eval.py) — primary quantitative signal
3. **raw score** (eval.py) — secondary; useful for diagnosing shaper interaction
4. **training loss** — dead last; has very little to do with what we're testing for

**Why:** Ninereeds is a Hebbian DLM — what matters is whether semantic circuits are forming and consolidating. Loss is next-token prediction fit; it can fall while clusters fragment or format bleeds. Shaped score catches output quality but not circuit structure. Brain_map is the MRI: it shows whether the right neurons are co-firing for the right concepts.

**Why brain_map is highest priority:** Two checkpoints with near-identical shaped scores (e.g. E2 0.989 vs E3 0.990) cannot be distinguished by eval alone. Brain_map cluster structure is the tiebreaker — and it may reveal that the higher-shaped checkpoint has a worse underlying circuit (fragmented hubs, cross-domain bleed, collapsed categories).

**How to apply:**
- After each epoch block completes, run brain_map with **both** language.jsonl and thinking.jsonl before picking a winner
- Do not promote a checkpoint as block winner without brain_map evidence
- Shaped score selects among candidates with similar brain_map profiles
- Loss numbers can be omitted from reports unless they show a clear anomaly (sudden spike = possible training bug)
- Never use loss alone to pick an epoch
