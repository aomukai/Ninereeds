# Ninereeds — Claude session guide

## What this project is

Ninereeds is a small Hebbian-trained AI. It trains on a hand-crafted corpus of structured
`[user]`/`[Ninereeds]` dialogue files. Because the model is small, there is no error
averaging from scale — every malformed training file has outsized impact. Quality gates
are more important here than in a typical project.

## Dispatch policy

**Claude handles:** planning, routing, verification, small targeted edits.
**DeepSeek handles:** bulk file I/O — rewriting, repairing, generating corpus files.

Do not use Claude tokens for corpus file work. Write a prompt, send it to DeepSeek,
read the result back, verify it, record progress. That is the full loop.

## Platform rules

| Mechanism | Works on | Notes |
|---|---|---|
| Direct OpenRouter API (urllib / openai client) | Windows + Linux | Preferred everywhere |
| `opencode` CLI subprocess | Linux only | `~/.opencode/bin/opencode` does not exist on Windows |
| bash scripts in `meta/scripts/` | Linux only | opencode wrappers |

**On Windows, never reach for opencode.** Use the direct API runners instead.
If you wake up on Linux and want to use opencode, confirm `~/.opencode/bin/opencode` exists first.

## Auth

All direct API runners read the key in this order:

1. `OPENROUTER_API_KEY` env var ← set this, works on both platforms
2. `OPENAI_API_KEY` env var (fallback)
3. `~/.local/share/opencode/auth.json` → `.openrouter.key` (Linux only, used by `worker_repair.py`)
4. `WORKER_API_KEY` env var (used by `worker_repair.py`)

## Repo structure

```
archive/          ← obsolete scripts, old prompts, historical artifacts
docs/             ← design docs, vision docs, reference notes
inventory/        ← allowlist.txt and other word/concept lists
loras/            ← LoRA adapter files
meta/
  scripts/        ← all batch runners, generators, verifiers
  workflow/       ← audit and analysis tools
tmp/              ← temporary outputs: logs, batch files, intermediate results
training/         ← training harness, rounds, logs, teacher skills
training_data/    ← corpus: phases, wiki, philosophy, reasoning, stories, lang
```

Root entry points (do not move): `bdh.py`, `train.py`, `inference.py`, `eval.py`,
`harness.py`, `prompt_shaper.py`.

## Tool index

### Cross-platform (direct API — use these on Windows or Linux)

**`meta/scripts/repair_formatting_opencode.py`** — formatting queue runner
- Queue: `training_data/phases/repair_formatting.txt`
- Progress: `training_data/phases/repair_progress_formatting.txt`
- Run: `python3 meta/scripts/repair_formatting_opencode.py --batch 250 --workers 6 --timeout 300`
- Verifies `[user]`/`[Ninereeds]` structure after every write; retries once on bad output
- Appends progress ledger only after confirmed write to disk

**`meta/scripts/extract_vocab.py`** — vocabulary extraction runner
- Extracts and normalises verbs, adjectives, nouns from any corpus directory
- Queue: any `files.txt` (absolute paths, one per line); progress: `files_done.txt` in same dir
- Run: `python3 meta/scripts/extract_vocab.py --queue training_data/wiki/files.txt --workers 4 --timeout 300`
- `max_tokens=32768` — do not lower; DeepSeek V4 Flash is a thinking model and reasoning tokens eat the budget before output is written. 16k causes `length` stop and truncated responses.
- Output: `nouns.txt`, `verbs.txt`, `adjectives.txt` in the queue's directory (deduped, sorted, merged incrementally)

**`meta/scripts/worker_repair.py`** — damage_map queue runner
- Queue: `training_data/phases/damage_map.txt`
- Uses `openai` client pointed at OpenRouter (install: `pip install openai`)
- Run: `python3 meta/scripts/worker_repair.py --batch 30 --workers 5`
- Claims entries before parallel work; returns failures to front of queue

**`meta/scripts/lang_gen.py`** — multilingual lang file generator
- Reads `inventory/allowlist.txt`, generates lang_1 files via DeepSeek
- Run: `python3 meta/scripts/lang_gen.py [--batch 10] [--workers 4] [--dry-run]`

**`meta/scripts/lang4.py`** — lang_4 structural corpus generator (4A/4B/4C)
- Jobs: hard-coded matrix (116 frames)
- Output: `training_data/lang/lang_4/` (files named `4a_*.md`, `4b_*.md`, `4c_*.md`)
- Run: `python3 meta/scripts/lang4.py gen --workers 4 --batch 5`

**`meta/scripts/lang4d.py`** — lang_4 story corpus generator (200 stories)
- Plans: `training_data/lang/lang_4d_plans.jsonl` · Output: `training_data/lang/lang_4/` (files named `4d_story_*.md`)
- Run: `python3 meta/scripts/lang4d.py plan --target 200` then `gen --workers 4`

**`meta/scripts/lang3c.py`** — lang_3c corpus generator (reflexive + benefactive)
- Verb list: `training_data/lang/lang_3c_verbs.txt`
- Jobs: `training_data/lang/lang_3_jobs.jsonl` · Progress: `lang_3_planned.txt`
- Output: `training_data/lang/lang_3/` (files named `3c_*.md`)
- Run: `python3 meta/scripts/lang3c.py plan --workers 4 --batch 10` then `gen --workers 4 --batch 5`

**`meta/scripts/lang5.py`** — lang_5 Q&A pair generator (91 files, all question types)
- Jobs: hard-coded matrix (5A wer/wen/wem/wessen, 5B wo/wohin/woher, 5C when, 5D why, 5E how, 5F yn/doch)
- Output: `training_data/lang/lang_5/` (files named `5a_*.md` … `5f_*.md`)
- Run: `python3 meta/scripts/lang5.py gen --workers 4 --batch 5`

**`meta/scripts/lang5d.py`** — lang_5 story generator (101 stories)
- Jobs: hard-coded list (73 original + 28 vocabulary context stories)
- Output: `training_data/lang/lang_5/` (files named `5d_story_*.md`)
- Run: `python3 meta/scripts/lang5d.py gen --workers 6`
- Report: `python3 meta/scripts/lang5d.py report`

**`meta/scripts/split_corpus.py`** — split multi-story/multi-entry files into individual files
- Triplet stories: `training_data/triplet_stories/tier_N/*.md` → one file per story (`category_NN_EN.md`)
- Philosophy: `training_data/philosophy/ninereeds_dialogues_catN.md` → one file per entry (`dialogues_catN_NN.md`)
- Run: `python3 meta/scripts/split_corpus.py triplet` or `philosophy`
- Already run; originals replaced with split files

**`meta/scripts/localize_reasoning.py`** — DE/JP/ZH monolingual localizations of reasoning files
- Source: `training_data/reasoning/*.md` (EN, no suffix)
- Output: `*_DE.md`, `*_JP.md`, `*_ZH.md` alongside each source
- Run: `python3 meta/scripts/localize_reasoning.py [--workers 3] [--lang DE,JP,ZH]`
- Already complete: 27 EN × 4 languages = 108 files

**`meta/scripts/localize_triplets.py`** — DE/JP/ZH monolingual localizations of triplet stories
- Source: `training_data/triplet_stories/tier_N/*_EN.md`
- Output: `*_DE.md`, `*_JP.md`, `*_ZH.md` alongside each source
- Run: `python3 meta/scripts/localize_triplets.py gen [--workers 8] [--batch 15] [--lang DE,JP,ZH]`
- Report: `python3 meta/scripts/localize_triplets.py report`
- Already complete: 1345 EN × 4 languages = 5380 files

**`meta/scripts/localize_philosophy.py`** — expand EN philosophy dialogues to multilingual format
- Rewrites `training_data/philosophy/dialogues_cat*.md` in place
- Each tag expanded: `[STATEMENT]` → `[STATEMENT_EN/DE/JA/ZH]`, same for `[USER]` and `[NINEREEDS]`
- Run: `python3 meta/scripts/localize_philosophy.py gen [--workers 4]`
- Report: `python3 meta/scripts/localize_philosophy.py report`
- Already complete: 144 files expanded

### Linux only (opencode)

**`meta/scripts/opencode_ds.sh`** — single DeepSeek call
- `meta/scripts/opencode_ds.sh prompt.txt` or `cat prompt.txt | meta/scripts/opencode_ds.sh`
- Reads API key from opencode auth store

**`meta/scripts/opencode_ds_fanout.sh`** — parallel fan-out
- `meta/scripts/opencode_ds_fanout.sh --workers 10 tmp/prompts/*.txt`
- One opencode process per prompt file; output lands in `tmp/opencode_fanout/`

### Audit and analysis (any platform, read-only)

| Script | Purpose |
|---|---|
| `meta/workflow/vocabulary_audit.py` | Scan corpus for vocabulary issues |
| `meta/workflow/vocabulary_gap_check.py` | Check coverage gaps |
| `meta/workflow/audit_documentation.py` | Documentation audit |
| `meta/scripts/build_dependency_graph.py` | Rebuild `inventory/dependency_graph.json` from phase file names |
| `meta/scripts/pos_check.py` | Part-of-speech validation |
| `meta/scripts/strip_opener.py` | Strip bad opener lines |
| `meta/scripts/extract_verbs.py` | Verb extraction for review |
| `meta/scripts/sort_allowlist_by_frequency.py` | Re-sort inventory/allowlist.txt by corpus frequency |

## Active queues (as of 2026-05-15)

| Queue | Total | Done | Remaining | Status |
|---|---|---|---|---|
| formatting | 275 | 275 | 0 | **DONE** |
| duplicate | 58 | 58 | 0 | **DONE** |

## Lang curriculum status (as of 2026-05-15)

All lang levels complete through Level 5:

| Level | Dir | Files | Notes |
|---|---|---|---|
| lang_1 | `lang_1/` | ~5k | One file per allowlist word; EN/DE/JP/ZH |
| lang_2 | `lang_2/` | ~6k | Semantic frames; adj/adv/noun/pronoun/combo |
| lang_3 | `lang_3/` | 615 | **Flat dir.** Prefix = sublevel: `3a_` dative double-object (83), `3b_` dative+genitive (33), `3c_` reflexive+benefactive (99), `3d_` parallel stories (400) |
| lang_4 | `lang_4/` | 316 | **Flat dir.** Prefix = sublevel: `4a_` static location (≈39), `4b_` movement (≈39), `4c_` instrument (≈38), `4d_` parallel stories (200) |
| lang_5 | `lang_5/` | 192 | **Flat dir.** Prefix = sublevel: `5a_` wer/wen/wem/wessen (41), `5b_` wo/wohin/woher (20), `5c_` when (8), `5d_` why+stories (7+101), `5e_` how (7), `5f_` yn+doch (8) |

**File naming convention (lang_3 through lang_5):** all files in a level live in one flat directory.
Filename prefix identifies the sublevel: `3a_verb.md`, `4b_prep_verb.md`, `5d_story_0001.md`, etc.

Templates: `training_data/lang/level_3a_templates.md`, `level_3b_templates.md`, `level_3c_templates.md`, `level_4_templates.md`, `level_5_templates.md`.

## Corpus structure

```
training_data/
  phases/
    phase_1/ … phase_6/   ← structured [user]/[Ninereeds] dialogue files
    repair_formatting.txt  ← formatting queue (done)
    repair_duplicate.txt   ← duplicate queue (done)
  lang/
    lang_1/               ← multilingual word files (EN/DE/JP/ZH), complete
    lang_2/               ← semantic frames (adj/adv/noun/pronoun/combo), complete
    lang_3/               ← flat; prefixed 3a_/3b_/3c_/3d_ (615 files), complete
    lang_4/               ← flat; prefixed 4a_/4b_/4c_/4d_ (316 files), complete
    lang_5/               ← flat; prefixed 5a_/5b_/5c_/5d_/5e_/5f_ (192 files), complete
    level_2a_templates.md ← lang_2 generation templates: verbs, adj/adv, nouns
    level_2b_templates.md ← lang_2 generation templates: pronouns, possession
    level_2c_templates.md ← lang_2 generation templates: combinations
    level_3a_templates.md ← lang_3 generation templates
    level_3b_templates.md ← lang_3 generation templates
    level_3c_templates.md ← lang_3 generation templates
    level_4_templates.md  ← lang_4 generation templates
    level_5_templates.md  ← lang_5 generation templates
  wiki/                   ← reference material
  triplet_stories/
    tier_1/ … tier_4/    ← narrative stories; 1345 files per language × 4 langs (EN/DE/JP/ZH)
                             naming: category_NN_EN.md, category_NN_DE.md, etc.
  reasoning/              ← reasoning + math examples; 27 EN files × 4 langs = 108 files
                             naming: filename.md (EN), filename_DE.md, filename_JP.md, filename_ZH.md
  philosophy/             ← philosophical dialogues; 144 multilingual files
                             naming: dialogues_catN_NN.md
                             tags: [STATEMENT_EN/DE/JA/ZH], [USER_EN/DE/JA/ZH], [NINEREEDS_EN/DE/JA/ZH]
```

## Corpus file format

Every phase file must have exactly 4 `[user]`/`[Ninereeds]` block pairs separated by blank lines.

```
[user]what does X look like?
[Ninereeds]This is X.
X is [property].
X is [property].
X is [property].
X is [property].
X is [property].
X is [A] and [B].

[user]where does X appear?
...
```

Rules:
- `[Ninereeds]` opener is on the same line as the tag: `[Ninereeds]This is X.`
- 5 body lines after the opener, 1 summary combining two properties
- One sentence per line, one period per line
- No pronouns (it, its, they, them, he, she, etc.)
- No negation in body lines
- Subject of every line is X or a part of X

## Hard constraints

- Never modify `bdh.py` or anything in `core/` (model weights live there when training runs)
- No training run until a full corpus audit returns GO
- Only mark queue items done with file-level evidence (read the file back after write)
- Do not start vocabulary rewrites without user sign-off
