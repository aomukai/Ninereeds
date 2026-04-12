# Wiki Implementation TODO

Working implementation queue for the Level 1 wiki.

This file is the practical companion to:
- `training_data/wiki/wiki_category_backlog.md` — strategic category backlog
- `training_data/wiki/CORPUS_STATUS.md` — current corpus state
- `training_data/phase 1 to 5/rewritten/missing_curriculum_terms.md` — curriculum-side anchor gaps

Use this file for the next concrete writing and review steps.

---

## Current priorities

The current goal is not "write everything fast."
The current goal is:

1. finish partial foundational categories
2. add missing high-utility daily-life categories in dependency order
3. periodically check whether new wiki vocabulary needs earlier anchoring in `phase 1–5`

---

## Next 10 categories to implement

These are the next best targets after the cleanup sprint.
They are ordered for dependency flow, not just by interest.

1. `School Life and Learning`
   Notes: expand the existing stub with everyday school life terms like `recess`, `teacher`, `student`, `backpack`, `school bus`, `subject`, `grade`.

2. `Clothing and Apparel`
   Notes: expand the current file with high-frequency items and closure terms like `shirt`, `shoe`, `sock`, `jacket`, `dress`, `zipper`, `mitten`, `skirt`.

3. `Money, Trade, and Shopping`
   Notes: expand the current file with `change`, `allowance`, `penny`, `nickel`, `dime`, `quarter`, `shopkeeper`, `customer`.

4. `Movement and Physical Action`
   Notes: finish the action vocabulary that lives between verbs, body, and play.

5. `Directions and Navigation`
   Notes: finish the travel and route side that builds on the cleaned `space` file.

6. `Meals and Mealtime Talk`
   Notes: useful bridge between foods, routines, family, and social interaction.

7. `Sensory Experiences`
   Notes: useful bridge between body, STEM, emotions, and food.

8. `Daily Routines and Self-Care`
   Notes: this is the first major missing category after the early partials.

9. `States of Being and Condition`
   Notes: needed for ordinary talk like `open`, `closed`, `full`, `empty`, `clean`, `dirty`, `broken`, `fixed`.

10. `Body States and Internal Cues`
    Notes: useful for hunger, thirst, pain, tiredness, comfort, and self-report.

---

## After the next 10

These are the next wave once the above is stable:

11. `Wants, Needs, and Preferences`
12. `Greetings and Social Salutations`
13. `Waiting and Patience`
14. `Containers and Capacity`
15. `Manners, Politeness, and Social Etiquette`
16. `Communication Acts and Language`
17. `Agreement and Disagreement`
18. `Ownership and Sharing`
19. `Friends and Peer Interactions`
20. `Personal Identity and Self-Description`

---

## Recurring review loop

Run these checks every few category additions, not just at the very end.

### 1. Anchor drift review

Question:
Does a newly written wiki entry rely on words that feel too ungrounded in `phase 1–5`?

Action:
- add the word to `missing_curriculum_terms.md` if it feels important and reusable
- note whether the word needs a phase anchor, a later phase concept file, or is safe to remain wiki-only

Examples already noticed:
- `thought`
- `real`
- `reality`
- `true`
- `truth`
- `money`

### 2. Duplicate ownership review

Question:
Did a new category accidentally create a second full anchor for a concept that already has a better home?

Action:
- keep one canonical `what is X?` home whenever possible
- move or cut duplicates before they spread into later expansion levels

### 3. Dangling contrast review

Question:
Did a new entry introduce `X is not Y` where `Y` has no entry yet?

Action:
- either implement `Y`
- or change the contrast to an already grounded concept

### 4. Register review

Question:
Does the file still sound like preschool/1st-grade educational material?

Warning signs:
- textbook compression
- hidden mechanism explanations
- adult therapeutic language
- taxonomy voice
- too many facts per sentence

### 5. Ordering review

Question:
Does the file go from broader anchors to narrower concepts?

Action:
- parent concept first
- specific examples later
- relation-heavy entries after the objects they depend on

---

## Small implementation rules

- Finish `PARTIAL` categories before starting too many new siblings.
- Prefer categories that unlock many later categories.
- Keep category identity clean; do not let files become catch-all buckets.
- If a concept belongs equally to two domains, choose one canonical home early.
- Add checklist comments at the top of files when obvious later additions are known.

---

## Good stopping points

A category batch is in a good temporary state when:

- the file has a clear anchor or anchors
- the prose matches current Level 1 voice
- there are no obvious duplicate concept homes
- the file order mostly goes from general to specific
- any important new anchor gaps are logged
