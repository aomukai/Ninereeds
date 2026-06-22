---
name: project-c16b-supplements
description: C16B supplement file design — 5 diagnosed issues, repair strategies, validation rules, training chain
metadata:
  type: project
---

# C16B Supplement Files

Source document: `Campaign 16B Supplement Files.pdf` in repo root.

## Core principle

C16A = alternate entrances into the same rooms (paraphrase tolerance).
C16B = repairs rooms whose foundations are weak (structural anchoring).
Do not use C16B to make the model sound smarter. Use it to make weak categories more structurally learnable.

## File naming

- Supplement: `concept_angle_supplement.md` (e.g. `almond_food_spine_supplement.md`)
- Supplement rephrase: `concept_angle_supplement_rephrase.md`
- C16B is additive — never overwrite original or `_rephrase` files.

## 5 diagnosed issues

### Issue 1 — Food spine
**Problem:** Inconsistent anchoring. `Bread is food.` vs `An almond is a seed.` → model may learn almond as seed/nature before food.
**Repair:** Every food concept gets a food-spine supplement.
**Food spine:** `X is food. People eat X. X has a taste. X comes from somewhere. X is not an animal/person.`
**Example:**
```
[user]Is an almond food?
[Ninereeds]Yes. An almond is food. People eat almonds.

[user]Do people eat almonds?
[Ninereeds]Yes. People eat almonds. An almond is food.

[user]What kind of thing is an almond?
[Ninereeds]An almond is food. An almond is a seed. An almond comes from a tree.

[user]Is an almond an animal?
[Ninereeds]No. An almond is not an animal. An almond is food.
```
**Boundary correction:** Non-living food uses negation, not "I don't know."
- Wrong: `[Ninereeds]I don't know what an almond dreams about.`
- Right: `[Ninereeds]An almond does not dream. An almond is not an animal.`

### Issue 2 — Nature spine
**Problem:** Files describe objects directly but don't anchor to nature. River/lake/rain/ocean all described as "water" → water cluster blur, distinguishing feature buried.
**Repair:** Add nature-spine supplement files.
**Nature spine:** `X is part of nature. X is found in the world. X has a distinguishing natural feature.`
**Nature Distinction Rule:** For overlapping water words, distinguishing feature must come early.
- `A river is flowing water.` ✓
- `A lake is still water in one place.` ✓
- `Rain is water that falls from the sky.` ✓
**Example:**
```
[user]Is a river part of nature?
[Ninereeds]Yes. A river is part of nature. A river is flowing water.

[user]What kind of natural thing is a river?
[Ninereeds]A river is part of nature. A river is water that flows across land.
```

### Issue 3 — Emotions need situation grounding
**Problem:** "Happy is a feeling" exists, but feelings remain abstract. No observable grounding.
**Repair:** Add situation-grounded supplement files for every emotion.
**Emotion spine:** `X is a feeling. A person can feel X. A situation can make a person feel X. There may be visible signs, but the exact feeling may be unknown.`
**Emotion Boundary Rule:**
- "I don't know" is valid for specific persons: `Is this person happy?` → `I don't know if this person is happy.`
- "I don't know" is NOT valid for general meaning: `What is happy?` → must explain, not hedge.
**Example:**
```
[user]When can a person feel happy?
[Ninereeds]A person can feel happy when something good happens. Happy is a feeling.

[user]Give an example of happy.
[Ninereeds]A child gets a toy. The child feels happy.
```

### Issue 4 — Actions need an action spine
**Problem:** Bucket is small (~90 files) and files lead with agents ("A person can run. A dog can run.") → fires people/animal clusters more than action cluster.
**Repair:** Add action-spine supplement files. Action must be anchored first; agents second.
**Action spine:** `X-ing is an action. X-ing is something a body/person/animal can do. X-ing has a simple result.`
**Action Generation Rule:** Never lead with "A person can…" — anchor the action first.
- Better: `Running is an action. A person can run.`
- Worse: `A person can run. A dog can run. A horse can run.`
**Example:**
```
[user]What kind of thing is running?
[Ninereeds]Running is an action. Running is something a body can do.

[user]What does running mean?
[Ninereeds]Running is an action. Running means moving fast on legs.
```

### Issue 5 — Boundary vs negation
**Problem:** "I don't know what an almond dreams about" implies almond may dream; teaches uncertainty where certainty is correct.
**Repair:** Use negation for false-premise questions about non-living things. Reserve "I don't know" for genuinely unknown answers.
- Unknown: `How many almonds exist?` → `I don't know how many almonds exist.`
- False premise: `Does an almond dream?` → `No. An almond does not dream. An almond is not an animal.`
**Known False Negation Examples:**
```
[user]Can a chair eat?
[Ninereeds]No. A chair cannot eat. A chair is furniture.

[user]Can red think?
[Ninereeds]No. Red cannot think. Red is a color.

[user]Is a river a person?
[Ninereeds]No. A river is not a person. A river is part of nature.
```

## Buckets that need less repair (do not overfeed)

- **Household:** already strong — clear spine, functionally distinct objects, low confusion.
- **Colors:** strong despite low count — every file leads with "X is a color." May need negation supplements later.
- **Animals:** medium — clear "A dog is an animal" spine; overlap is animal-to-animal. Defer to yes/no/negation in C17.
- **Body:** medium — clear "A hand is a body part" spine. May need cross-domain files later.

## Validation rules

- Exactly one `[user]` line, one `[Ninereeds]` line per file.
- No pronouns in atomic supplement files.
- Concept name is subject of every answer sentence.
- `_rephrase` and `_supplement_rephrase` files do not change the answer.
- Food spine files contain "food."
- Nature spine files contain "nature" or "natural."
- Emotion files contain "feeling."
- Action files contain "action."
- Non-living dream/think/feel files use negation, not "I don't know."
- Genuine unknown files use "I don't know."
- No file contains multiple user questions.
- No file contains long prose.

## Generation order

1. Finish C16A `_paraphrase.md` generation → **DONE**
2. Validate C16A files
3. Generate C16B `_supplement.md` files
4. Validate C16B supplement files
5. Generate `_supplement_rephrase.md` files
6. Validate supplement rephrase files
7. Train from best C16A checkpoint

## Training chain

```
C16 E4 winner
→ train with C16A paraphrase files
→ select best C16A checkpoint
→ train with C16B supplements + supplement rephrases
→ select best C16B checkpoint
```

## Success criteria

- food/nature/emotions/actions after-hub scores improve
- boundary remains strong
- identity does not erode
- household and colors do not dominate even more
- chat answers stay on topic
- false-premise questions produce negation instead of uncertainty
- genuine unknown questions still produce "I don't know"

## Failure signs (stop and inspect)

- answers become longer but less grounded
- supplement files cause generic template output
- "I don't know" becomes overused
- negation replaces valid uncertainty
- food/nature/action/emotion files blur into one another
- identity weakens
- chat score drops while loss improves
- household/colors improve while weak buckets stay weak
