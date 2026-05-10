# Handoff — 2026-05-10

## What just happened (this session)

**Triplet story pipeline: all 4 tiers complete for 141 backfill word triplets.**

- `training_data/triplet_stories/tier_1/` — 141 stories (pure description, 6-8 sentences, no pronouns, one "is not")
- `training_data/triplet_stories/tier_2/` — 141 stories (named character, 1-2 dialogue lines, pronouns allowed)
- `training_data/triplet_stories/tier_3/` — 141 stories (causal reasoning with "because/so", 3 paragraphs)
- `training_data/triplet_stories/tier_4/` — 141 stories (First/After/Finally structure, if-then conditionals)

All 564 stories verified against the allowlist and assembled into 13 category files per tier.

---

## What's next: wiki entries

**447 words need wiki entries.** Classification is in `tmp/wiki_classification.txt`:
- Format per line: `word | L1 | category_slug`
- 398 L1 words, 48 L2 words, 1 L3 word
- L1 = direct definition entry; L2 = builds on L1 concepts; L3 = abstract/complex

**Target:** append entries into the existing category files in `training_data/wiki/wiki_1/` (and `wiki_2/` for L2 words). Each word gets one `[user]what is/does/are X?` → `[Ninereeds]...` block appended to its category file.

**Existing format** (look at any `training_data/wiki/wiki_1/*.md` for reference):
```
[user]what is a beak?
[Ninereeds]A beak is the hard pointed mouth of a bird. Birds use beaks to pick up food, break seeds, and drink water. A beak can be long and thin or short and wide depending on what the bird eats. Beaks are made of bone covered with a hard layer. A beak is not a mouth with teeth.
```

Key rules (same as all Ninereeds content):
- All content words must be on the allowlist (`training_data/allowlist.txt` or `tmp/allowlist_full.txt`)
- Function words are free (the, a, is, not, to, of, etc.)
- End each entry with "X is not Y" (the contrast/negative definition pattern)
- 4-6 sentences per entry
- No pronouns in wiki entries (these are L1-style definitional, not narrative)

**How to generate:** Dispatch to DeepSeek via opencode fanout. One prompt per word, pointing at the allowlist, outputting the `[user]/[Ninereeds]` block. The word's category determines which file to append to.

Look at `meta/scripts/generate_t1_prompts.py` for the prompt-generation pattern. You'll want a new `meta/scripts/generate_wiki_prompts.py` that reads `tmp/wiki_classification.txt` and emits one prompt file per word.

---

## Scripts built this session (all in `meta/scripts/`)

| Script | Purpose |
|---|---|
| `generate_t1_prompts.py` | Generate tier-1 prompts from `tmp/triplet_table.md` |
| `generate_t2_prompts.py` | Generate tier-2 prompts from T1 output (reads character used) |
| `generate_t3_prompts.py` | Generate tier-3 prompts from T2 output (extracts character name) |
| `generate_t4_prompts.py` | Generate tier-4 prompts from T3 output (extracts character name) |
| `verify_t1_stories.py` | Verify T1: 6-8 sentences, one "is not", no pronouns, allowlist |
| `verify_t2_stories.py` | Verify T2: 8-16 sentences, dialogue, character name, allowlist |
| `verify_t3_stories.py` | Verify T3: 7-16 sentences, "because" ≥1, dialogue, allowlist |
| `verify_t4_stories.py` | Verify T4: 10-20 sentences, "First"/"Finally", "if", dialogue, allowlist |
| `assemble_t1_stories.py` | Append verified T1 stories to tier_1 category files (idempotent) |
| `assemble_t2_stories.py` | Same for tier_2 (idempotent — skips already-present [user] lines) |
| `assemble_t3_stories.py` | Same for tier_3 |
| `assemble_t4_stories.py` | Same for tier_4 |
| `run_triplet_pipeline.sh` | Orchestrator: verify → assemble → dispatch next tier; uses flag files |

---

## Triplet table

`tmp/triplet_table.md` — 141 rows across 13 categories (animals_and_nature, body_and_health, food_and_meals, home_and_daily_life, people_and_relationships, play_and_games, tools_and_making, vehicles_and_travel, weather_and_seasons, school_and_learning, language_and_grammar, math_and_science, abstract_concepts). Format: `| # | Anchor | Support 1 | Support 2 | Scenario hint |`

Character names used in T2-T4 are deterministic: `CHARACTERS[(num-1) % 13]` from the list `[cody, ella, emma, jack, lily, luke, max, noah, nora, owen, sophie, toby, will]`. Surnames on allowlist: brown, hall, lee.

---

## Pipeline patterns and gotchas

**Wrong-path writes:** DeepSeek workers consistently wrote ~8-11 out of 141 stories to wrong paths (e.g. `tmp/triplet_stories/` instead of `tmp/triplet_t2_output/`). Always do a rescue pass after batch completion:
1. Find missing files (compare prompt list vs output dir)
2. Scan JSONL for `"tool": "write"` → get actual path → copy to correct location
3. If no write event: extract `[user]...[Ninereeds]...` text block from JSONL
4. If no text either: re-dispatch with fresh job

**Verifier false positives fixed this session:**
- Pronouns (he/she/him/her/etc.) not in `allowlist_full.txt` → added to `FUNCTION_WORDS` in all verify scripts
- `ies→y` suffix rule missing → `blueberries`/`hurries` etc. were flagging; added rule to all verify scripts
- Ordinal numbers (fifth, sixth…) and `ever`/`though` → added to `FUNCTION_WORDS` in verify_t4
- HTML entities (`&quot;`) in 2 stories → fixed with `sed -i 's/&quot;/"/g'`
- Irregular past tense gaps → added `knelt`, `crept`, `drank` and ~20 more to IRREGULAR dict

**Allowlist reference:**
- `training_data/allowlist.txt` — canonical content word list (~5247 words, one per line)
- `tmp/allowlist_full.txt` — 19,514 words extracted from all phase training text; used by verify scripts

**Persistent bad words:** When DeepSeek keeps using a banned word after one redispatch, add explicit `FORBIDDEN WORD: X — do not use it, use Y instead` to the prompt. Worked on second attempt for most; 3 stories needed manual `sed` edits (single-word swaps: `realizes`→`notices`, `fizz`→`bubble`, `offstage`→`behind the stage`).

---

## State of tmp/ artifacts

```
tmp/triplet_table.md               — 141-row planning table (do not edit)
tmp/triplet_t1_output/             — 141 verified tier-1 story files
tmp/triplet_t2_output/             — 141 verified tier-2 story files
tmp/triplet_t3_output/             — 141 verified tier-3 story files
tmp/triplet_t4_output/             — 141 verified tier-4 story files
tmp/triplet_t{1,2,3,4}_prompts/   — prompt files (keep for re-dispatch reference)
tmp/triplet_t{1,2,3,4}_violations.txt  — last verification report per tier
tmp/t{2,3,4}_assembled.flag        — sentinel files; delete to re-run a pipeline step
tmp/wiki_classification.txt        — 447 words with level and category, ready for wiki generation
tmp/allowlist_full.txt             — 19,514-word verify allowlist
```

---

## Wiki generation plan (next session)

1. Write `meta/scripts/generate_wiki_prompts.py`:
   - Read `tmp/wiki_classification.txt` (447 lines, format: `word | L1 | category`)
   - Generate one prompt per word: ask DeepSeek for a 4-6 sentence wiki entry in `[user]/[Ninereeds]` format
   - Include the allowlist path and the "X is not Y" ending rule
   - Output prompt to `tmp/wiki_prompts/word.txt`
   - Encode target file path in prompt: `training_data/wiki/wiki_1/<category>_entries.md`

2. Dispatch: `bash meta/scripts/opencode_ds_fanout.sh --workers 10 tmp/wiki_prompts/*.txt`

3. Rescue pass: same pattern as triplet stories — some workers will write to wrong paths; scan JSOLs and copy.

4. Verify: write `meta/scripts/verify_wiki_entries.py` (check format, sentence count, allowlist, "is not" ending)

5. Assemble: `meta/scripts/assemble_wiki_entries.py` (append to category files, idempotent — skip if [user] line already present)

Note: some category files already exist in `training_data/wiki/wiki_1/` from prior work. The assembler must append, not overwrite, and skip duplicates.
