# Phase 6 Bridge Manifest

Canonical ordered manifest for the active Phase 6 bridge curriculum files.

Status: `phase_6_01.md` through `phase_6_12.md` drafted and landed.

## Purpose

This file is the canonical ordered manifest for the current Phase 6 bridge curriculum.

Each file records:
- file name
- concept family
- target words
- prerequisite words/files
- required pattern-grid frames
- implementation status

## Family order

1. Foundation / meta-language
2. Thought / knowledge
3. Truth / reasoning
4. Communication
5. Planning / sequence
6. Epistemic uncertainty / evidence
7. Practical support vocabulary
8. Symbolic and judgment vocabulary

## Manifest table

| Planned file | Family | Target words | Depends on | Required patterns | Status |
|---|---|---|---|---|---|
| `phase_6_01.md` | Foundation | thing, object, word, sentence | Phase 1-5 | "A X is a thing.", "A word is a part of speaking.", "A sentence is a group of words." | completed |
| `phase_6_02.md` | Meta-language | meaning, question, answer, language | `phase_6_01.md` | "A word has a meaning.", "A question asks for an answer." | completed |
| `phase_6_03.md` | Thought / Knowledge | thought, idea, think, know, learn, understand | `phase_6_02.md` | "A thought is in the mind.", "An idea is a new thought." | completed |
| `phase_6_04.md` | Truth / Reasoning | true, real, fact, reason, because | `phase_6_03.md` | "A fact is a true thing.", "X is real because Y." | completed |
| `phase_6_05.md` | Communication | ask, explain, say, repeat, tell | `phase_6_02.md` | "The child asks a question.", "The teacher explains the meaning." | completed |
| `phase_6_06.md` | Planning / Sequence | plan, goal, step, first, next, follow | `phase_6_05.md` | "A plan has steps.", "First do X, next do Y." | completed |
| `phase_6_07.md` | Epistemic | maybe, uncertain, certainly, probably | `phase_6_04.md` | "Maybe X.", "Certainly, X is true." | completed |
| `phase_6_08.md` | Epistemic 2 | possibly, evidence, justification, proof | `phase_6_07.md` | "Evidence shows truth.", "Proof removes doubt." | completed |
| `phase_6_09.md` | Logic / Action | try, wait, hurt, finally | `phase_6_06.md` | "To try is to work.", "Finally, X happens." | completed |
| `phase_6_10.md` | Logic / Math | equal, math, right, phrase | `phase_6_09.md` | "Equal means the same.", "A phrase is a group of words." | completed |
| `phase_6_11.md` | Practical / Status | ready, enough, better, money | `phase_6_06.md`, `phase_6_10.md` | "The soup is ready.", "The bowl has enough rice.", "A dry coat is better.", "Money can buy food." | completed |
| `phase_6_12.md` | Symbolic / Judgment | cent, letter, opinion, reality | `phase_6_04.md`, `phase_6_10.md`, `phase_6_11.md` | "A cent is part of money.", "A letter is part of a word.", "An opinion tells what a person likes.", "Reality is all real things and events." | completed |

## File details

### `phase_6_11.md` — Practical / Status
- **Focus**: high-frequency readiness, sufficiency, comparison, and transaction support words.
- **Words**: `ready`, `enough`, `better`, `money`.
- **Patterns**:
  - "The soup is ready for dinner."
  - "The bowl has enough rice."
  - "A dry coat is better than a wet coat."
  - "Money can buy food or a toy."

### `phase_6_12.md` — Symbolic / Judgment
- **Focus**: compact symbol-level and judgment vocabulary that later wiki/story layers assume.
- **Words**: `cent`, `letter`, `opinion`, `reality`.
- **Patterns**:
  - "A cent is a small part of money."
  - "A letter is part of a word."
  - "An opinion tells what a person likes or thinks."
  - "Reality is all real things and events."

## Next steps

1. If more curriculum backfill is needed, derive the next bounded batch from `training_data/cross_corpus_introduced_vocabulary_ledger.md` instead of expanding this manifest ad hoc.
2. Keep `training_data/phases/phase_1_6_backfill_plan.md` as the short planning/status rollup for what has already landed and what still remains.
3. Re-run dependency-graph verification after any future Phase 6 additions.
