# Training Activation Audit

**Go / No-go: GO**

Date: 2026-05-22

## Corpus summary

| Layer | Files | Notes |
|---|---|---|
| lang_1 | 5,147 | all pass |
| lang_2 | 6,837 | all pass |
| phase_1 | 1,450 | all pass; 130 minor fixes (whitespace/CRLF) |
| phase_2 | 740 | all pass; 119 fixed |
| phase_3 | 1,387 | all pass; 121 fixed |
| lang_3 | 615 | all pass |
| lang_4 | 316 | all pass |
| phase_4 | 261 | all pass; 59 fixed |
| phase_5 | 376 | all pass; 120 fixed |
| phase_6 | 1,592 | all pass; 317 fixed |
| lang_5 | 192 | all pass |
| wiki_1 | 112 | all pass |
| wiki_2 | 33 | all pass |
| wiki_3 | 4 | all pass |
| wiki_4 | 3 | all pass; 1 fixed |
| reasoning | 108 | all pass; 1 fixed |
| triplet_tier_1 | 1,364 | all pass; 45 fixed (leading space on [user]) |
| triplet_tier_2 | 1,348 | all pass; 1 tag typo fixed directly |
| triplet_tier_3 | 1,304 | all pass; 14 fixed |
| triplet_tier_4 | 1,364 | all pass; 17 fixed |
| philosophy | 144 | all pass |
| **Total** | **24,697** | **946 minor fixes; 0 skipped** |

## Fixes applied

- Trailing whitespace and CRLF line endings: normalized throughout
- Extra `[Ninereeds]` tags on body lines (24 files): stripped to one opener per block
- Leading space after `[user]` tag in triplet stories (76 files): removed
- Broken tag typo in `tier_2/food_and_meals_20_ZH.md`: repaired directly
- Phase files with 1–3 pairs (intentional format variant): included as valid

## Assembled corpus

Path: `training/corpus/full_corpus.txt`
Size: 13.30 MB (13,946,969 bytes)
Build script: `meta/scripts/build_training_corpus.py`
Build report: `training/corpus/build_report.txt`

## Sign-off

All 24,697 corpus files pass format validation.
Corpus assembled and verified.
Training is cleared to begin — GO.
