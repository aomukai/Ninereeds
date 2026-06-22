---
name: Ninereeds project overview
description: What Ninereeds is, its goal, and why corpus quality gates matter so much
type: project
originSessionId: f214e64f-85e7-459c-96c1-d360ca2cd70b
---
Ninereeds is a small AI trained via Hebbian/association-based learning — not gradient descent. Because the model is small, there is no error averaging from scale. Every training pair either reinforces a correct association or a wrong one, permanently.

**Why:** This means quality gates matter more here than in any normal LLM fine-tuning project. "Mostly right" doesn't exist — garbage in is garbage out, directly.

**How to apply:** Never approve bulk changes without verifying quality. Every phase file, wiki article, story, and reasoning file must meet strict format rules. When in doubt, spot-check before accepting a worker's receipt.

The end goal is a closed, controlled language corpus — finite and complete within its scope. Unknown-word gaps are handled by Ninereeds asking for clarification, not by expanding the vocabulary. The corpus doesn't need to be exhaustive; it needs to be coherent.
