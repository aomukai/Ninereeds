# Story Rewrite Prompt Notes

This file is no longer the canonical source of story-shape rules.

Use these files instead:
- `training_data/triplet_stories/story_tier_specs.md` — canonical Tier 1 / Tier 2 rewrite-stage shape and goals
- `training_data/triplet_stories/review_queue.md` — Tier 1 one-file-at-a-time cleanup order
- `training_data/triplet_stories/tier_2/review_queue.md` — Tier 2 one-file-at-a-time creation order
- `training_data/wiki/story_layer_rules.md` — broader cross-layer rules, vocabulary guardrails, and later-layer guidance

## Minimal worker framing

Read the selected queue item and rewrite only that file.
Follow `story_tier_specs.md` exactly for the target tier.
Keep vocabulary grounded, keep scenes concrete, and do not rewrite unrelated files.

## Tier 1 prompt skeleton

```text
Read the whole file and rewrite every story in it.
Follow `training_data/triplet_stories/story_tier_specs.md` for Tier 1 exactly.
Do not ask questions.
Do not explain what you are doing.
Output only the rewritten stories.
```

## Tier 2 prompt skeleton

```text
Read the whole file and create the Tier 2 version of every story in it.
Follow `training_data/triplet_stories/story_tier_specs.md` for Tier 2 exactly.
Do not ask questions.
Do not explain what you are doing.
Output only the rewritten stories.
```
