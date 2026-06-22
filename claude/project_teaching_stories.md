---
name: project-teaching-stories
description: Design of teaching stories corpus — bird's eye view, 4-lingual Rosetta Stone format, grammar tiers
metadata:
  type: project
---

Teaching stories replace the old B/D/E phase files. They live in `training_data/teaching_stories/`.

**Purpose:** language teaching (like phase files), NOT concept teaching (that's grounded_stories).

**Format:** One file per concept. Each file = the same story localised into 4 languages in order: EN → DE → JP → ZH. Plain `[user]`/`[Ninereeds]` tags. Same facts/events across all languages — natural localisation, not literal translation.

**Tiers (grammar complexity, not vocabulary):**
- Tier 1: Picture-book grammar. 5–8 word sentences, one idea each, simple past/present.
- Tier 2: Picture-book, slightly expanded. Short sentences, may join with "and"/"but".
- Tier 3: 1st-grade grammar. Slightly longer, may use "because"/"when"/"then".
- Tier 4: 2nd-grade grammar. Two dialogue turns per language (8 blocks total). "Although"/"until" OK.

**Narrator:** Omniscient, bird's eye. NO named characters (Emma/Taro/Gran/Biscuit/Bello belong to grounded_stories only). Use "a child", "an old woman", "a dog", etc.

**Setting:** Village world — path, field, market, hedge, millpond, barn, oak tree, well, garden, doorstep.

**JP:** plain form only (never です/ます). **ZH:** Traditional Chinese only (never Simplified).

**Generator:** `meta/scripts/story_gen_v2.py` — living list with floor=3, standard=5 targets per word.
