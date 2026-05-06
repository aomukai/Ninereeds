# Codex Handoff — 2026-05-07

Read this file first in the next session.

## Current State

- Branch: `main`
- HEAD before this handoff commit: `69725ff`
- `origin/main` is behind local `main` by 3 commits before this handoff commit:
  - `5aec960` `add verb discovery files and this-is inventories`
  - `ae5cb86` `add this-is opener review classifications`
  - `69725ff` `review and remove safe this-is openers`

The repo is in a good checkpoint state. The next session should start from this document and then continue with the remaining `this is` cleanup and later repair buckets.

## What We Did This Session

### Completed earlier in this cleanup sequence

1. Deleted 19 `UNKNOWN` placeholder files from phase 2.
   - Source list: [`training_data/phases/repair_placeholder.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_placeholder.txt)

2. Fixed article errors in 18 files.
   - Source list: [`training_data/phases/repair_article_errors.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_article_errors.txt)
   - Receipt: [`training_data/phases/repair_receipt_articles.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_receipt_articles.txt)

3. Fixed deterministic Q-format deviations.
   - Source list: [`training_data/phases/repair_formatting.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_formatting.txt)
   - Receipt: [`training_data/phases/repair_receipt_qformat.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_receipt_qformat.txt)

4. Repaired adjective-as-noun files using the adjective frame from [`training_data/phases/phase_3/phase_3_103.md`](/home/aomukai/Ninereeds/training_data/phases/phase_3/phase_3_103.md).
   - Queue: [`training_data/phases/repair_adj_as_noun.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_adj_as_noun.txt)
   - Receipt: [`training_data/phases/repair_receipt_adj.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_receipt_adj.txt)
   - Progress: [`training_data/phases/repair_progress_adj.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_progress_adj.txt)

5. Repaired verb-as-noun files using the verb frame from [`training_data/phases/phase_5/phase_5_1880.md`](/home/aomukai/Ninereeds/training_data/phases/phase_5/phase_5_1880.md).
   - Queue: [`training_data/phases/repair_verb_as_noun.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_verb_as_noun.txt)
   - Dispatch list: [`training_data/phases/repair_verb_as_noun_dispatch.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_verb_as_noun_dispatch.txt)
   - Receipt: [`training_data/phases/repair_receipt_verb.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_receipt_verb.txt)
   - Progress: [`training_data/phases/repair_progress_verb.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_progress_verb.txt)

6. Removed 2 false positives and deleted 3 grammar/function-word files from the verb bucket.
   - Deleted:
   - [`training_data/phases/phase_6/phase_6_608.md`](/home/aomukai/Ninereeds/training_data/phases/phase_6/phase_6_608.md)
   - [`training_data/phases/phase_6/phase_6_628.md`](/home/aomukai/Ninereeds/training_data/phases/phase_6/phase_6_628.md)
   - [`training_data/phases/phase_6/phase_6_947.md`](/home/aomukai/Ninereeds/training_data/phases/phase_6/phase_6_947.md)

7. Moved the noun allowlist to `meta/`.
   - Allowlist: [`meta/allowed_nouns.txt`](/home/aomukai/Ninereeds/meta/allowed_nouns.txt)
   - Generator updated: [`training_data/phases/scan.py`](/home/aomukai/Ninereeds/training_data/phases/scan.py)

### Discovery and review infrastructure added

8. Built verb discovery artifacts:
   - [`meta/ing_mean_grep.txt`](/home/aomukai/Ninereeds/meta/ing_mean_grep.txt)
   - [`meta/ing_is_to_grep.txt`](/home/aomukai/Ninereeds/meta/ing_is_to_grep.txt)
   - [`meta/ing_source_first_verbs.txt`](/home/aomukai/Ninereeds/meta/ing_source_first_verbs.txt)
   - [`meta/verbs_already_taught_from_ing_sources.txt`](/home/aomukai/Ninereeds/meta/verbs_already_taught_from_ing_sources.txt)
   - [`meta/verbs_not_yet_taught_from_ing_sources.txt`](/home/aomukai/Ninereeds/meta/verbs_not_yet_taught_from_ing_sources.txt)

9. Built `This is ...` inventories:
   - Extractor: [`meta/extract_ninereeds_openers.py`](/home/aomukai/Ninereeds/meta/extract_ninereeds_openers.py)
   - Lists:
   - [`training_data/phases/this_is.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is.txt)
   - [`training_data/phases/this_is_a.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_a.txt)
   - [`training_data/phases/this_is_an.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_an.txt)
   - [`training_data/phases/this_is_the.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_the.txt)

10. Built the weird/pathology review files.
   - Weird list to keep as an artifact:
   - [`training_data/phases/this_is_weird.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_weird.txt)
   - Review input builder:
   - [`meta/build_this_is_review_input.py`](/home/aomukai/Ninereeds/meta/build_this_is_review_input.py)
   - Review input:
   - [`training_data/phases/this_is_review_input.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_review_input.txt)

11. Dispatched DeepSeek to classify the `this is` review set.
   - Prompt:
   - [`meta/this_is_review_prompt.txt`](/home/aomukai/Ninereeds/meta/this_is_review_prompt.txt)
   - Flags:
   - [`training_data/phases/this_is_review_flags.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_review_flags.txt)
   - Receipt:
   - [`training_data/phases/this_is_review_receipt.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_review_receipt.txt)
   - Classification counts:
   - `SAFE_REMOVE`: 80 rows
   - `BAD_DETERMINER`: 76 rows
   - `DEEPER_PATHOLOGY`: 37 rows

12. Split the review flags into bucket files.
   - [`training_data/phases/this_is_safe_remove.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_safe_remove.txt)
   - [`training_data/phases/this_is_bad_determiner.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_bad_determiner.txt)
   - [`training_data/phases/this_is_deeper_pathology.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_deeper_pathology.txt)
   - Unique file list for safe pass:
   - [`training_data/phases/this_is_safe_remove_files.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_safe_remove_files.txt)

13. Dispatched DeepSeek to remove safe `This is ...` openers.
   - Prompt:
   - [`meta/this_is_safe_remove_prompt.txt`](/home/aomukai/Ninereeds/meta/this_is_safe_remove_prompt.txt)
   - Progress:
   - [`training_data/phases/this_is_safe_remove_progress.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_safe_remove_progress.txt)
   - Receipt:
   - [`training_data/phases/this_is_safe_remove_receipt.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_safe_remove_receipt.txt)
   - Skipped log:
   - [`training_data/phases/this_is_safe_remove_skipped.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_safe_remove_skipped.txt)

## Important Nuance About The Safe-Remove Run

The worker receipt is misleading about whether edits happened during the final invocation.

What actually happened:
- The first useful worker attempt edited the 20 target files and wrote the progress ledger.
- A later resumed invocation saw the files already changed, then wrote a receipt/skipped log saying no `[Ninereeds]This is` openers remained.
- I verified directly in the corpus that the edits are real and correct.

Verified invariant on all 20 files in [`training_data/phases/this_is_safe_remove_files.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_safe_remove_files.txt):
- each file still has 4 `[Ninereeds]` lines
- each file now has 0 `[Ninereeds]This is` lines

## Where We Are Now

### Completed and stable

- adjective repair bucket: done
- verb repair bucket: done
- placeholder deletions: done
- article fixes: done
- deterministic Q-format fixes: done
- safe `this is` opener removals: first bounded bucket done

### Still pending

1. Review and repair the `BAD_DETERMINER` bucket.
   - Main file:
   - [`training_data/phases/this_is_bad_determiner.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_bad_determiner.txt)
   - These are cases like `This is the yolk.` where the problem is deeper than opener removal.

2. Review and repair the `DEEPER_PATHOLOGY` bucket.
   - Main file:
   - [`training_data/phases/this_is_deeper_pathology.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_deeper_pathology.txt)
   - These include pronouns, adverbs, malformed grammar, and ontology trouble.

3. Later unresolved repair queues still kept in `training_data/phases/`:
   - [`training_data/phases/repair_abstract_as_object.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_abstract_as_object.txt)
   - [`training_data/phases/repair_duplicate.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_duplicate.txt)
   - [`training_data/phases/repair_formatting.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_formatting.txt)
   - [`training_data/phases/repair_teleology.txt`](/home/aomukai/Ninereeds/training_data/phases/repair_teleology.txt)

## Recommended Next Steps

1. Read this file first.

2. Check whether local `main` has been pushed.
   - At handoff creation time, local commits since `origin/main` are expected to include:
   - `5aec960`
   - `ae5cb86`
   - `69725ff`
   - plus the handoff commit that adds this file

3. Continue with the `BAD_DETERMINER` bucket as the next bounded DeepSeek task.
   - Likely process:
   - inspect a representative sample from [`training_data/phases/this_is_bad_determiner.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_bad_determiner.txt)
   - define rewrite policy
   - dispatch DeepSeek on a compact file list or labeled review file

4. Keep [`training_data/phases/this_is_weird.txt`](/home/aomukai/Ninereeds/training_data/phases/this_is_weird.txt).
   - Do not rename or delete it.
   - User explicitly wants it preserved for context and likely future writing.

## Quick Resume Prompt

Use this in the next session:

`Read /home/aomukai/Ninereeds/codex_handoff_2026-05-07.md and continue from there.`
