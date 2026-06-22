---
name: Ninereeds next task — vocabulary governance pass
description: The next major task: audit all content words against wordlist.txt, get human sign-off, then rewrite flagged files
type: project
originSessionId: f214e64f-85e7-459c-96c1-d360ca2cd70b
---
Precondition met as of 2026-05-06: damage check complete, phase files confirmed final.

The goal: Every content word in the corpus is either explicitly taught in phases 1–6, or is a deliberate reviewed exception. No silent vocabulary scope creep.

The process (pass by pass, not one batch):
1. Extract all content words (nouns/verbs/adj/adv) from all corpus files. Lemmatize. Record word + every filename it appears in.
2. Check against training_data/phases/wordlist.txt. Flag anything not taught in phases 1–6.
3. Filter flagged words by syllable complexity (target: grade 3–4 ceiling). Prefer syllable count over Flesch-Kincaid — FK scores are suppressed by short lines and give false negatives.
4. Produce a table: word | file_count | filenames | decision for human review.
5. **Human review checkpoint** — user decides keep or remove for each flagged word.
6. DeepSeek rewrites flagged files using allowed-words palette (wordlist.txt + approved additions). NOT mechanical search+replace — model picks best fit in context.
7. Re-scan any new files created in step 6. Repeat until clean.

Key constraints:
- Do NOT start bulk rewrites without user sign-off on the rewrite list.
- Coverage/entry decisions (whether a kept word needs a new phase entry, wiki article, or story) are always human calls.
- Track what was added each pass — cascade tracking matters.

**Why:** The user needs to control which words enter the allowed set; Claude does not make that call.

**How to apply:** When the user initiates vocab governance, start with step 1 (extraction). Do not proceed to rewrites until the user has reviewed and signed off on the flagged-word table.
