---
name: project-teaching-stories-rationale
description: Why teaching stories are designed the way they are — research rationale, not just spec
metadata:
  type: project
---

## Why teaching stories exist

Campaign 13 showed that B/D/E concepts (emotions, cognitive verbs, abstraction) cannot be absorbed from the static property-listing format used in phase files. The model regressed every time, across 4 attempts each. The hypothesis: these concepts need narrative grounding — they need to be *shown in action* before they can be described as properties.

Teaching stories are the pre-grounding layer. They introduce B/D/E concepts through story before the phase files try to define them.

## Why omniscient narrator, no named characters

Teaching stories sit *before* grounded_stories in the curriculum. The named characters (Emma, Taro, Gran, Biscuit, Bello) are introduced gradually across the 195 grounded stories — Bello doesn't appear until story 48. Pre-naming them in teaching stories would break that sequencing.

The bird's eye view earns the anonymity naturally. From that vantage, "a child" and "an old woman" are the right level of specificity. It also removes world-building inconsistencies (e.g. why doesn't the postman know Gran's name in a small village?).

## Why grammar tiers, not content tiers

The vocabulary comes from the allowlist regardless of tier — the script handles that through the support words system. What scales is grammar complexity: picture-book sentence structure at tier 1, elementary school at tier 4. The model needs to see the same vocabulary in progressively more complex grammatical contexts.

## Why localisation not translation

The four-language Rosetta Stone effect requires each version to read naturally to a native speaker. Literal translation produces calques and unnatural phrasing that trains bad patterns. The facts and events of the story are the same across all four languages; the phrasing is idiomatic in each. JP uses plain form only (never です/ます). ZH uses Traditional Chinese only.

## Why the same story in all four languages

The purpose is language teaching, not concept variation. Seeing the same scene in EN, DE, JP, ZH gives the model cross-lingual alignment — it can learn that the same event maps to different grammatical structures across languages. grounded_stories can tell different stories because their purpose is concept grounding through narrative variety. Teaching stories need consistency across languages for the alignment signal to work.

## Relationship to grounded_stories

grounded_stories = concept teaching, close-up immersive prose, named characters, no [user]/[Ninereeds] structure.
Teaching stories = language teaching, bird's eye omniscient narrator, same village world, [user]/[Ninereeds] Q&A format.

They use the same setting (the village) but serve different purposes and use different formats. Teaching stories come first in curriculum; grounded_stories introduce the named characters afterward.
