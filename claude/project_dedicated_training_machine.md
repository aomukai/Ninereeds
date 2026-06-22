---
name: dedicated-training-machine
description: Planned dedicated headless training machine with 2x RTX 3060 12GB — timeline and intended use
metadata:
  type: project
---

Dedicated headless training machine planned with 2× RTX 3060 12GB.

**Why:** Current setup shares training card (CUDA:0) with daily workload; batch size sometimes reduced to 4 due to GPU contention; eval must wait for training to finish or run on daily-use card.

**Timeline:** Parts purchase ~July 2026; target completion before August 2026, August at latest.

**Intended use:** Machine runs 24/7, training only. Options once live:
- Two simultaneous training runs (ordering experiments in parallel)
- Train on one card, run eval + corpus work on the other
- Headless — no user workload competing for VRAM

**How to apply:** Once the machine is online, curriculum ordering questions (interleaved vs. sequential triplets, grounded before/after teaching stories, etc.) can be answered by running both variants simultaneously rather than sequentially. Current ~15-hour epoch times could be parallelised.
