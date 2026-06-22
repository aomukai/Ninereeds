---
name: Ninereeds corpus structure
description: Directory layout and content types in training_data/
type: project
originSessionId: f214e64f-85e7-459c-96c1-d360ca2cd70b
---
training_data/
  phases/          — Phase 1–6: word-by-word curriculum (most basic → most abstract)
  wiki/wiki_1–4/   — Article-style topic entries (levels 1–4)
  triplet_stories/ — [user]/[Ninereeds] training stories (tiers 1–4)
  reasoning/       — Math/logic reasoning corpus (sprints 0–4)
  philosophy/      — Dialogue-style philosophy files
  dependency_graph.json  — Machine-readable graph of all content (2052 nodes as of 2026-05-04)

Phase files follow a strict template: 4 Q&A pairs, third person, no pronouns before a clear noun referent, no first/second person, specific format rules per phase. Phase 1 has slightly different Q2 and Q4 forms from phases 2–6 — this distinction matters for quality review.

**Why:** The format rules enforce the learning curriculum. Deviation silently corrupts training.

**How to apply:** When reviewing any phase file, check format against the phase-specific template. Phase 1 ≠ Phase 2+ format.
